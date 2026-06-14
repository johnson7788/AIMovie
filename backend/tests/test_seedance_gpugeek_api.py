import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

_module_path = (
    Path(__file__).resolve().parent.parent
    / "tools"
    / "video_generator_doubao_seedance_gpugeek_api.py"
)
_spec = importlib.util.spec_from_file_location(
    "video_generator_doubao_seedance_gpugeek_api", _module_path
)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
_extract_api_error = _mod._extract_api_error
VideoGeneratorDoubaoSeedanceGPUGEEKAPI = _mod.VideoGeneratorDoubaoSeedanceGPUGEEKAPI


class TestSeedanceGpugeekErrors(unittest.TestCase):
    def test_extract_nested_error(self):
        response = {
            "status": "failed",
            "error": {"message": "output audio sensitive content", "type": "moderation"},
        }
        self.assertIn("output audio sensitive content", _extract_api_error(response))

    def test_extract_logs(self):
        response = {
            "status": "failed",
            "logs": [{"message": "upstream rejected prompt"}],
        }
        self.assertIn("upstream rejected prompt", _extract_api_error(response))

    def test_fallback_status(self):
        response = {"status": "failed"}
        self.assertEqual(_extract_api_error(response), "Task failed with status: failed")


class TestSeedanceGpugeekFallback(unittest.IsolatedAsyncioTestCase):
    async def test_multi_image_rejection_retries_first_ref_before_text_only(self):
        gen = VideoGeneratorDoubaoSeedanceGPUGEEKAPI(generate_audio=True)
        calls = []

        async def fake_generate_once(prompt, refs, resolution, aspect_ratio, duration, *, generate_audio=None):
            calls.append((list(refs), generate_audio))
            if len(calls) == 1:
                raise ValueError(
                    "Video creation failed (HTTP 400): "
                    "The request failed because the input image may contain real person."
                )
            return "ok"

        with patch.object(gen, "_generate_once", side_effect=fake_generate_once):
            result = await gen.generate_single_video(
                prompt="prompt",
                reference_image_paths=["first.png", "last.png"],
                resolution="720p",
                aspect_ratio="16:9",
                duration=5,
                style="cinematic",
            )

        self.assertEqual(result, "ok")
        self.assertEqual(calls[0][0], ["first.png", "last.png"])
        self.assertEqual(calls[1][0], ["first.png"])

    async def test_real_person_rejection_never_retries_refs(self):
        gen = VideoGeneratorDoubaoSeedanceGPUGEEKAPI(generate_audio=True)
        calls = []

        async def fake_generate_once(prompt, refs, resolution, aspect_ratio, duration, *, generate_audio=None):
            calls.append((list(refs), generate_audio))
            if len(calls) == 1:
                raise ValueError(
                    "Video creation failed (HTTP 400): "
                    "The request failed because the input image may contain real person."
                )
            if len(calls) == 2:
                raise ValueError("temporary text-only failure")
            return "ok"

        with patch.object(gen, "_generate_once", side_effect=fake_generate_once), \
             patch("asyncio.sleep", return_value=None):
            result = await gen.generate_single_video(
                prompt="prompt",
                reference_image_paths=["first.png"],
                resolution="720p",
                aspect_ratio="16:9",
                duration=5,
                style="cinematic",
            )

        self.assertEqual(result, "ok")
        self.assertEqual(calls[0][0], ["first.png"])
        self.assertEqual(calls[1][0], [])
        self.assertEqual(calls[2][0], [])


if __name__ == "__main__":
    unittest.main()
