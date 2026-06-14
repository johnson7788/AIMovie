"""Integration + unit tests for shot end-frame handoff (last-frame pipeline)."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

from utils.pipeline_consistency import resolve_shot_end_reference, video_last_frame_path
from utils.video import extract_last_frame_from_video


def _write_color_video(path: str, *, width: int = 320, height: int = 240, fps: int = 24, seconds: float = 1.0) -> None:
    """Create a short mp4: first half red, second half blue (last frame should be blue)."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"OpenCV VideoWriter failed for {path}")

    total_frames = max(2, int(fps * seconds))
    mid = total_frames // 2
    try:
        for index in range(total_frames):
            color = (0, 0, 255) if index < mid else (255, 0, 0)  # BGR: red then blue
            writer.write(np.full((height, width, 3), color, dtype=np.uint8))
    finally:
        writer.release()


def _mean_blue_channel(png_path: str) -> float:
    image = cv2.imread(png_path)
    if image is None:
        raise AssertionError(f"Could not read extracted frame: {png_path}")
    return float(np.mean(image[:, :, 0]))


def _mean_red_channel(png_path: str) -> float:
    image = cv2.imread(png_path)
    if image is None:
        raise AssertionError(f"Could not read extracted frame: {png_path}")
    return float(np.mean(image[:, :, 2]))


class TestLastFrameExtraction(unittest.TestCase):
    def test_extract_last_frame_ffmpeg_or_moviepy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "clip.mp4")
            output_path = os.path.join(tmpdir, "video_last_frame.png")
            _write_color_video(video_path, width=640, height=480, seconds=3.0)

            result = extract_last_frame_from_video(video_path, output_path)

            self.assertEqual(result, output_path)
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 100)
            # Last segment is blue in BGR → high blue channel mean.
            self.assertGreater(_mean_blue_channel(output_path), 200.0)
            # First segment is red; the extracted continuity frame must not be the first frame.
            self.assertLess(_mean_red_channel(output_path), 80.0)

    def test_resolve_prefers_api_last_frame_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "shots", "0")
            os.makedirs(shot_dir, exist_ok=True)
            video_path = os.path.join(shot_dir, "video.mp4")
            _write_color_video(video_path)

            expected = video_last_frame_path(0, tmpdir)
            extract = MagicMock(side_effect=AssertionError("extract should not run when API URL succeeds"))

            with patch("utils.image.download_image") as download:
                download.side_effect = lambda url, save_path: open(save_path, "wb").write(b"fake-api-frame")

                result = resolve_shot_end_reference(
                    tmpdir,
                    0,
                    video_path,
                    extract,
                    api_last_frame_url="https://example.com/last.png",
                )

            self.assertEqual(result, expected)
            download.assert_called_once()
            extract.assert_not_called()

    def test_resolve_uses_ffmpeg_extract_before_storyboard_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "shots", "1")
            os.makedirs(shot_dir, exist_ok=True)
            video_path = os.path.join(shot_dir, "video.mp4")
            first_frame = os.path.join(shot_dir, "first_frame.png")
            last_frame = os.path.join(shot_dir, "last_frame.png")
            _write_color_video(video_path)
            with open(first_frame, "wb") as handle:
                handle.write(b"first")
            with open(last_frame, "wb") as handle:
                handle.write(b"last")

            def _extract(video: str, out: str) -> str:
                with open(out, "wb") as handle:
                    handle.write(b"extracted-end-frame")
                return out

            result = resolve_shot_end_reference(tmpdir, 1, video_path, _extract)

            expected = video_last_frame_path(1, tmpdir)
            self.assertEqual(result, expected)
            with open(expected, "rb") as handle:
                self.assertEqual(handle.read(), b"extracted-end-frame")

    def test_resolve_falls_back_to_storyboard_last_frame(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "shots", "2")
            os.makedirs(shot_dir, exist_ok=True)
            video_path = os.path.join(shot_dir, "video.mp4")
            storyboard_last = os.path.join(shot_dir, "last_frame.png")
            with open(video_path, "wb") as handle:
                handle.write(b"not-a-video")
            with open(storyboard_last, "wb") as handle:
                handle.write(b"storyboard-last")

            extract = MagicMock(side_effect=RuntimeError("ffmpeg failed"))
            result = resolve_shot_end_reference(tmpdir, 2, video_path, extract)

            self.assertEqual(result, storyboard_last)

    def test_resolve_weak_first_frame_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "shots", "3")
            os.makedirs(shot_dir, exist_ok=True)
            video_path = os.path.join(shot_dir, "video.mp4")
            first_frame = os.path.join(shot_dir, "first_frame.png")
            with open(video_path, "wb") as handle:
                handle.write(b"not-a-video")
            with open(first_frame, "wb") as handle:
                handle.write(b"weak-first")

            extract = MagicMock(side_effect=RuntimeError("ffmpeg failed"))
            result = resolve_shot_end_reference(tmpdir, 3, video_path, extract)

            self.assertEqual(result, first_frame)


if __name__ == "__main__":
    unittest.main()
