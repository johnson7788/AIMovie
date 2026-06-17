import importlib.util
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "image_generator_doubao_seedream_gpugeek_api.py"
_spec = importlib.util.spec_from_file_location("seedream_gpugeek_api", _MODULE_PATH)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
_map_size = _mod._map_size


class TestSeedreamGPUGEEKSize(unittest.TestCase):
    def test_sub_minimum_size_is_upscaled(self):
        mapped = _map_size("852x480")
        w, h = (int(part) for part in mapped.lower().split("x"))
        self.assertGreaterEqual(w * h, 3_686_400)
        self.assertNotEqual(mapped, "852x480")

    def test_at_minimum_size_unchanged(self):
        self.assertEqual(_map_size("2560x1440"), "2560x1440")


if __name__ == "__main__":
    unittest.main()
