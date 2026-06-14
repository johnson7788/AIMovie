import os
import tempfile
import unittest
from unittest.mock import MagicMock

from PIL import Image

from interfaces import ShotDescription
from pipelines.script2video_pipeline import Script2VideoPipeline
from utils.pipeline_consistency import (
    build_crossfade_schedule,
    resolve_shot_end_reference,
    should_use_serial_keyframe_pipeline,
)

def _shot(idx: int, cam_idx: int) -> ShotDescription:
    return ShotDescription(
        idx=idx,
        is_last=idx == 2,
        cam_idx=cam_idx,
        visual_desc=f"shot {idx}",
        variation_type="small",
        variation_reason="small variation",
        ff_desc="ff",
        ff_vis_char_idxs=[],
        lf_desc="lf",
        lf_vis_char_idxs=[],
        motion_desc="motion",
        audio_desc="audio",
    )


def _write_image(path: str, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (16, 16), color).save(path)


class TestPipelineConsistency(unittest.TestCase):
    def test_same_camera_short_blend(self):
        shots = [_shot(0, 0), _shot(1, 0), _shot(2, 0)]
        self.assertEqual(build_crossfade_schedule(shots), [0.08, 0.08])

    def test_different_camera_short_fade(self):
        shots = [_shot(0, 0), _shot(1, 1)]
        self.assertEqual(build_crossfade_schedule(shots), [0.2])

    def test_mixed_schedule(self):
        shots = [_shot(0, 0), _shot(1, 0), _shot(2, 1)]
        self.assertEqual(build_crossfade_schedule(shots), [0.08, 0.2])

    def test_resolve_shot_end_reference_uses_storyboard_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "shots", "1")
            os.makedirs(shot_dir, exist_ok=True)
            video_path = os.path.join(shot_dir, "video.mp4")
            first_frame = os.path.join(shot_dir, "first_frame.png")
            with open(video_path, "wb") as handle:
                handle.write(b"not a real video")
            with open(first_frame, "wb") as handle:
                handle.write(b"png")

            extract = MagicMock(side_effect=RuntimeError("ffmpeg failed"))
            result = resolve_shot_end_reference(tmpdir, 1, video_path, extract)

            self.assertEqual(result, first_frame)
            extract.assert_called_once()

    def test_serial_keyframe_enabled_for_single_camera(self):
        class _Cam:
            def __init__(self, idx):
                self.idx = idx

        self.assertTrue(should_use_serial_keyframe_pipeline([_Cam(0)]))
        self.assertFalse(should_use_serial_keyframe_pipeline([_Cam(0), _Cam(1)]))

    def test_serial_keyframe_enabled_for_short_episode(self):
        class _Cam:
            def __init__(self, idx):
                self.idx = idx

        requirement = "Target episode duration: approximately 15 seconds. Use at most 3 shots."
        self.assertTrue(should_use_serial_keyframe_pipeline([_Cam(0), _Cam(1)], requirement))

    def test_serial_handoff_prefers_single_first_frame_reference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "shots", "1")
            os.makedirs(shot_dir, exist_ok=True)
            first_frame = os.path.join(shot_dir, "first_frame.png")
            last_frame = os.path.join(shot_dir, "last_frame.png")
            prev_tail = os.path.join(tmpdir, "shots", "0", "video_last_frame.png")
            os.makedirs(os.path.dirname(prev_tail), exist_ok=True)
            _write_image(first_frame, (10, 20, 30))
            _write_image(prev_tail, (10, 20, 30))
            _write_image(last_frame, (200, 180, 160))

            pipeline = Script2VideoPipeline.__new__(Script2VideoPipeline)
            pipeline.working_dir = tmpdir
            pipeline._scene_anchor_path = None

            shot = _shot(1, 0)
            shot.variation_type = "medium"

            self.assertEqual(
                pipeline._build_video_reference_paths(shot, prev_tail),
                [first_frame],
            )

    def test_soft_handoff_regenerates_old_forced_first_frame(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "shots", "1")
            prev_dir = os.path.join(tmpdir, "shots", "0")
            os.makedirs(shot_dir, exist_ok=True)
            os.makedirs(prev_dir, exist_ok=True)
            first_frame = os.path.join(shot_dir, "first_frame.png")
            video_path = os.path.join(shot_dir, "video.mp4")
            prev_tail = os.path.join(prev_dir, "video_last_frame.png")
            _write_image(first_frame, (10, 20, 30))
            _write_image(prev_tail, (10, 20, 30))
            with open(video_path, "wb") as handle:
                handle.write(b"cached video")

            pipeline = Script2VideoPipeline.__new__(Script2VideoPipeline)
            pipeline.working_dir = tmpdir
            pipeline._prepare_soft_handoff_first_frame(1, prev_tail)

            self.assertFalse(os.path.exists(first_frame))
            self.assertFalse(os.path.exists(video_path))


if __name__ == "__main__":
    unittest.main()
