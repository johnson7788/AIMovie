import unittest

from utils.style_prompts import (
    expand_image_style_prompt,
    expand_video_style_prompt,
    is_live_action_style,
    is_real_person_rejection,
)


class TestStylePrompts(unittest.TestCase):
    def test_cinematic_image_is_live_action_not_anime(self):
        text = expand_image_style_prompt("cinematic")
        self.assertIn("film still", text.lower())
        self.assertIn("fictional virtual actor", text.lower())
        self.assertNotIn("anime", text.lower())

    def test_cinematic_reference_has_seedance_guardrail(self):
        text = expand_image_style_prompt("cinematic")
        self.assertIn("Reference image for AI video generation", text)
        self.assertIn("Not a photograph of a real celebrity", text)

    def test_cinematic_video_style(self):
        text = expand_video_style_prompt("cinematic")
        self.assertIn("photorealistic", text.lower())
        self.assertNotIn("anime", text.lower())

    def test_anime_stays_illustrated(self):
        text = expand_video_style_prompt("anime")
        self.assertIn("Anime", text)

    def test_storybook_is_illustrated(self):
        self.assertFalse(is_live_action_style("storybook"))
        self.assertIn("Storybook", expand_video_style_prompt("storybook"))

    def test_real_person_rejection_detection(self):
        msg = "Video creation failed (HTTP 400): The request failed because the input image may contain real person."
        self.assertTrue(is_real_person_rejection(msg))


if __name__ == "__main__":
    unittest.main()
