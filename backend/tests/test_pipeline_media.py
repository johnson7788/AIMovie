import unittest

from utils.pipeline_media import (
    SUPPORTED_ASPECT_RATIOS,
    aspect_ratio_llm_hint,
    concat_dimensions_for_aspect,
    dimensions_for_aspect,
    dimensions_for_aspect_min_pixels,
    frame_size_for_aspect,
    frame_image_size_for_resolution,
    portrait_turnaround_size,
    portrait_view_size,
    scene_image_size_for_aspect,
    image_size_for_aspect,
    resolve_aspect_ratio,
    sanitize_polished_script,
    resolve_max_shots_for_duration,
    seedance_shot_duration,
    SEEDANCE_SINGLE_CLIP_MAX_SECONDS,
    SEEDREAM_MIN_PIXELS,
)


class TestPipelineMedia(unittest.TestCase):
    def test_all_ui_ratios_have_dimensions(self):
        for ratio in SUPPORTED_ASPECT_RATIOS:
            width, height = dimensions_for_aspect(ratio)
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)
            self.assertEqual(width % 2, 0)
            self.assertEqual(height % 2, 0)

    def test_portrait_9_16(self):
        self.assertEqual(frame_size_for_aspect("9:16"), "720x1280")
        self.assertEqual(concat_dimensions_for_aspect("9:16"), (720, 1280))

    def test_landscape_16_9(self):
        self.assertEqual(frame_size_for_aspect("16:9"), "1280x720")
        self.assertEqual(image_size_for_aspect("16:9"), "2560x1440")
        self.assertEqual(
            dimensions_for_aspect_min_pixels("16:9"),
            (2560, 1440),
        )
        self.assertGreaterEqual(2560 * 1440, SEEDREAM_MIN_PIXELS)

    def test_portrait_image_size_meets_seedream_minimum(self):
        width, height = dimensions_for_aspect_min_pixels("9:16")
        self.assertEqual(image_size_for_aspect("9:16"), f"{width}x{height}")
        self.assertGreaterEqual(width * height, SEEDREAM_MIN_PIXELS)

    def test_frame_image_size_matches_video_resolution(self):
        self.assertEqual(frame_image_size_for_resolution("16:9", "480p"), "852x480")
        self.assertEqual(frame_image_size_for_resolution("9:16", "480p"), "480x852")
        self.assertEqual(frame_image_size_for_resolution("16:9", "720p"), "1280x720")

    def test_scene_and_portrait_reference_sizes(self):
        self.assertEqual(scene_image_size_for_aspect("16:9"), "2560x1440")
        width, height = (int(p) for p in portrait_turnaround_size().split("x"))
        self.assertGreaterEqual(width * height, SEEDREAM_MIN_PIXELS)
        self.assertEqual(width, height * 3)
        self.assertEqual(portrait_view_size(), image_size_for_aspect("1:1"))

    def test_seedance_single_clip_and_duration(self):
        self.assertEqual(resolve_max_shots_for_duration(10), 1)
        self.assertEqual(resolve_max_shots_for_duration(15), 1)
        self.assertEqual(resolve_max_shots_for_duration(30), 3)
        self.assertEqual(seedance_shot_duration(10, 1), 10)
        self.assertEqual(seedance_shot_duration(15, 1), 15)
        self.assertEqual(SEEDANCE_SINGLE_CLIP_MAX_SECONDS, 15)

    def test_resolve_explicit_over_text(self):
        self.assertEqual(
            resolve_aspect_ratio("Aspect ratio: 16:9", explicit="9:16"),
            "9:16",
        )

    def test_aspect_ratio_llm_hint_landscape(self):
        self.assertIn("landscape", aspect_ratio_llm_hint("16:9").lower())
        self.assertIn("竖屏", aspect_ratio_llm_hint("16:9"))

    def test_aspect_ratio_llm_hint_portrait(self):
        self.assertIn("portrait", aspect_ratio_llm_hint("9:16").lower())
        self.assertIn("横屏", aspect_ratio_llm_hint("9:16"))

    def test_sanitize_polished_script_strips_meta_and_fixes_label(self):
        raw = (
            "好的，剧本医生已就位。我将严格遵循您的创作要求，"
            "将这段短剧场景进行优化，使其更符合15秒、16:9竖屏的短视频叙事节奏。\n\n"
            "---\n\n**SCENE 1 - EXT. STREET (16:9竖屏)**\n\n阿青站在面摊前。"
        )
        cleaned = sanitize_polished_script(raw, aspect_ratio="16:9")
        self.assertTrue(cleaned.startswith("**SCENE"))
        self.assertNotIn("剧本医生", cleaned)
        self.assertNotIn("16:9竖屏", cleaned)
        self.assertIn("16:9横屏", cleaned)


if __name__ == "__main__":
    unittest.main()
