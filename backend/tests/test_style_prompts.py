import unittest

from utils.style_prompts import expand_style_prompt, is_real_person_rejection


class TestStylePrompts(unittest.TestCase):
    def test_expand_storybook_includes_fictional_suffix(self):
        text = expand_style_prompt("storybook")
        self.assertIn("Storybook", text)
        self.assertIn("not a photograph of a real person", text)

    def test_expand_unknown_style_still_safe(self):
        text = expand_style_prompt("custom look")
        self.assertIn("custom look", text)
        self.assertIn("fictional", text.lower())

    def test_real_person_rejection_detection(self):
        msg = "Video creation failed (HTTP 400): The request failed because the input image may contain real person."
        self.assertTrue(is_real_person_rejection(msg))


if __name__ == "__main__":
    unittest.main()
