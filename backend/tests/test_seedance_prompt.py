import unittest

from utils.seedance_prompt import build_seedance_video_prompt


class TestSeedancePrompt(unittest.TestCase):
    def test_dialogue_formatted_for_speech(self):
        prompt = build_seedance_video_prompt(
            motion_desc="Static camera. The young man trembles.",
            audio_desc=(
                '[Dialogue] Lin Feng (determined whisper): "I clear my own path."\n'
                "[Sound Effect] Ambient sound: creaking wood"
            ),
            duration_seconds=5,
        )
        self.assertIn('Lin Feng (determined whisper) says: "I clear my own path."', prompt)
        self.assertIn("Spoken dialogue", prompt)
        self.assertIn("audible character speech", prompt)
        self.assertIn("creaking wood", prompt)

    def test_multiple_dialogues_get_timeline(self):
        prompt = build_seedance_video_prompt(
            motion_desc="Two-shot conversation.",
            audio_desc=(
                '[Dialogue] Alice (happy): "Hello."\n'
                '[Dialogue] Bob (calm): "Hi there."'
            ),
            duration_seconds=6,
        )
        self.assertIn('0-3s:', prompt)
        self.assertIn('3-6s:', prompt)


if __name__ == "__main__":
    unittest.main()
