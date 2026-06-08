"""Integration tests for character portrait generation.

Tests the turnaround sheet approach (single image → crop into 3 views)
with real API calls. Requires valid API credentials in environment.

Usage:
    # Skip if no API key (default)
    python -m pytest tests/test_character_portraits.py -v

    # Run with GPUGeek
    GPUGEEK=your_key python -m pytest tests/test_character_portraits.py -v

    # Run with Volcengine
    ARK_API_KEY=your_key python -m pytest tests/test_character_portraits.py -v

    # Skip integration tests (run unit tests only)
    SKIP_INTEGRATION=1 python -m pytest tests/test_character_portraits.py -v
"""

import importlib
import importlib.machinery
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---- stub heavy deps that aren't needed for portrait tests ----
_STUB_MODULES = [
    "moviepy",
    "cv2",
    "scenedetect", "scenedetect.detectors",
    "faiss",
    "google", "google.genai", "google.genai.types", "google.genai.errors",
    "langchain_community", "langchain_community.vectorstores",
    "langchain_community.vectorstores.FAISS",
]
for _mod in _STUB_MODULES:
    if _mod not in sys.modules:
        mock = MagicMock()
        mock.__spec__ = importlib.machinery.ModuleSpec(_mod, None)
        mock.__path__ = []
        sys.modules[_mod] = mock


def _make_character(idx=0, name="TestHero"):
    """Create a minimal valid CharacterInScene for portrait tests."""
    from interfaces import CharacterInScene

    return CharacterInScene(
        idx=idx,
        identifier_in_scene=name,
        is_visible=True,
        static_features=f"{name} is a young warrior with short black hair and brown eyes, "
                       f"wearing a blue leather jacket and dark pants.",
        dynamic_features="Standing confidently with a neutral expression.",
    )


def _get_image_generator():
    """Try to create a real image generator from available API keys.

    Returns (generator, provider_name) or (None, reason) if no key is available.
    """
    # Try GPUGeek first
    gpugeek_key = os.environ.get("GPUGEEK", "")
    if gpugeek_key:
        from tools.image_generator_doubao_seedream_gpugeek_api import (
            ImageGeneratorDoubaoSeedreamGPUGEEKAPI,
        )
        return ImageGeneratorDoubaoSeedreamGPUGEEKAPI(api_key=gpugeek_key), "gpugeek"

    # Try Volcengine
    ark_key = os.environ.get("ARK_API_KEY", "")
    if ark_key:
        from tools.image_generator_doubao_seedream_volcengine_api import (
            ImageGeneratorDoubaoSeedreamVolcengineAPI,
        )
        return ImageGeneratorDoubaoSeedreamVolcengineAPI(api_key=ark_key), "volcengine"

    return None, "No API key found (set GPUGEEK or ARK_API_KEY)"


class TestTurnaroundSheetUnit(unittest.TestCase):
    """Unit tests that don't require API calls."""

    def test_prompt_template_formatting(self):
        """Turnaround sheet prompt should format correctly with character data."""
        from agents.character_portraits_generator import prompt_template_turnaround

        prompt = prompt_template_turnaround.format(
            identifier="Hero",
            features="(static) A brave knight; (dynamic) Holding a sword",
            style="fantasy illustration",
        )
        self.assertIn("Hero", prompt)
        self.assertIn("brave knight", prompt)
        self.assertIn("fantasy illustration", prompt)
        self.assertIn("FRONT VIEW", prompt)
        self.assertIn("SIDE VIEW", prompt)
        self.assertIn("BACK VIEW", prompt)
        self.assertIn("LEFT panel", prompt)
        self.assertIn("CENTER panel", prompt)
        self.assertIn("RIGHT panel", prompt)

    def test_prompt_has_consistency_wording(self):
        """Prompt must include strong consistency language."""
        from agents.character_portraits_generator import prompt_template_turnaround

        self.assertIn("EXACT SAME", prompt_template_turnaround)
        self.assertIn("perfect consistency", prompt_template_turnaround.lower())

    def test_crop_turnaround_views_horizontal(self):
        """crop_turnaround_views should split a horizontal image into 3 equal parts."""
        from PIL import Image
        from utils.image import crop_turnaround_views

        # Create a 900x300 test image with 3 colored regions
        sheet = Image.new("RGB", (900, 300), "white")
        for i, color in enumerate(["red", "green", "blue"]):
            for x in range(i * 300, (i + 1) * 300):
                for y in range(300):
                    sheet.putpixel((x, y), {
                        "red": (255, 0, 0),
                        "green": (0, 255, 0),
                        "blue": (0, 0, 255),
                    }[color])

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = crop_turnaround_views(sheet, tmpdir, ["front", "side", "back"])

            self.assertEqual(len(paths), 3)
            for name in ["front", "side", "back"]:
                self.assertIn(name, paths)
                self.assertTrue(os.path.exists(paths[name]))

            # Each cropped image should be ~300x300
            from PIL import Image as PILImage
            for name in ["front", "side", "back"]:
                img = PILImage.open(paths[name])
                self.assertEqual(img.size, (300, 300))
                img.close()

    def test_crop_turnaround_views_vertical(self):
        """crop_turnaround_views should split a vertical image into 3 equal parts."""
        from PIL import Image
        from utils.image import crop_turnaround_views

        sheet = Image.new("RGB", (300, 900), "white")
        for i, color in enumerate(["red", "green", "blue"]):
            for y in range(i * 300, (i + 1) * 300):
                for x in range(300):
                    sheet.putpixel((x, y), {
                        "red": (255, 0, 0),
                        "green": (0, 255, 0),
                        "blue": (0, 0, 255),
                    }[color])

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = crop_turnaround_views(
                sheet, tmpdir, ["top", "middle", "bottom"], horizontal=False
            )
            self.assertEqual(len(paths), 3)
            from PIL import Image as PILImage
            for name in ["top", "middle", "bottom"]:
                img = PILImage.open(paths[name])
                self.assertEqual(img.size, (300, 300))
                img.close()

    def test_image_output_to_pil_b64(self):
        """image_output_to_pil should decode base64 ImageOutput."""
        import base64
        from io import BytesIO
        from PIL import Image
        from utils.image import image_output_to_pil
        from interfaces.image_output import ImageOutput

        # Create a small PNG, encode to base64
        img = Image.new("RGB", (100, 50), "yellow")
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

        output = ImageOutput(fmt="b64", ext="png", data=b64_str)
        result = image_output_to_pil(output)
        self.assertEqual(result.size, (100, 50))

    def test_image_output_to_pil_pil(self):
        """image_output_to_pil should return PIL ImageOutput as-is."""
        from PIL import Image
        from utils.image import image_output_to_pil
        from interfaces.image_output import ImageOutput

        img = Image.new("RGB", (200, 100), "blue")
        output = ImageOutput(fmt="pil", ext="png", data=img)
        result = image_output_to_pil(output)
        self.assertIs(result, img)

    def test_generator_has_all_methods(self):
        """CharacterPortraitsGenerator should have turnaround + legacy methods."""
        from agents import CharacterPortraitsGenerator

        self.assertTrue(hasattr(CharacterPortraitsGenerator, "generate_turnaround_sheet"))
        self.assertTrue(hasattr(CharacterPortraitsGenerator, "generate_front_portrait"))
        self.assertTrue(hasattr(CharacterPortraitsGenerator, "generate_side_portrait"))
        self.assertTrue(hasattr(CharacterPortraitsGenerator, "generate_back_portrait"))


class TestTurnaroundSheetIntegration(unittest.TestCase):
    """Integration tests that make real API calls."""

    @classmethod
    def setUpClass(cls):
        """Check for API key once before all integration tests."""
        if os.environ.get("SKIP_INTEGRATION"):
            raise unittest.SkipTest("SKIP_INTEGRATION is set")

        cls.generator, cls.provider = _get_image_generator()
        if cls.generator is None:
            raise unittest.SkipTest(f"No API key available ({cls.provider})")

        from agents.character_portraits_generator import CharacterPortraitsGenerator

        cls.portraits_gen = CharacterPortraitsGenerator(image_generator=cls.generator)
        cls.character = _make_character()

    def test_generate_turnaround_sheet_and_crop(self):
        """Full pipeline: generate turnaround sheet → crop into 3 views."""
        import asyncio
        from utils.image import image_output_to_pil, crop_turnaround_views

        async def run():
            # Step 1: Generate turnaround sheet
            output = await self.portraits_gen.generate_turnaround_sheet(
                self.character,
                style="illustration, clean lines, solid white background",
            )
            self.assertIsNotNone(output)
            self.assertIsNotNone(output.data)

            # Step 2: Convert to PIL
            sheet_pil = image_output_to_pil(output)
            width, height = sheet_pil.size
            print(f"\n  Turnaround sheet size: {width}x{height} (provider={self.provider})")
            self.assertGreater(width, 100)
            self.assertGreater(height, 100)

            # Step 3: Crop into 3 views
            with tempfile.TemporaryDirectory() as tmpdir:
                paths = crop_turnaround_views(sheet_pil, tmpdir)
                self.assertEqual(len(paths), 3)

                # Step 4: Verify all 3 files exist and have content
                from PIL import Image as PILImage

                for view_name in ["front", "side", "back"]:
                    path = paths[view_name]
                    self.assertTrue(os.path.exists(path), f"Missing {view_name}.png")
                    self.assertGreater(os.path.getsize(path), 100,
                                       f"{view_name}.png is too small")

                    # Check dimensions
                    img = PILImage.open(path)
                    view_w, view_h = img.size
                    print(f"  {view_name}: {view_w}x{view_h}")
                    self.assertGreater(view_w, 50, f"{view_name} too narrow")
                    self.assertGreater(view_h, 100, f"{view_name} too short")
                    img.close()

            return paths

        paths = asyncio.run(run())
        print(f"  Generated portrait paths: {paths}")

    def test_turnaround_sheet_retry_on_failure(self):
        """generate_turnaround_sheet should be decorated with retry."""
        from agents.character_portraits_generator import CharacterPortraitsGenerator
        import inspect

        # Check that the method has the retry decorator attribute
        method = CharacterPortraitsGenerator.generate_turnaround_sheet
        self.assertTrue(hasattr(method, "retry"),
                        "generate_turnaround_sheet should have @retry decorator")


if __name__ == "__main__":
    unittest.main()
