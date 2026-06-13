import importlib.util
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
