import unittest

from utils.progress_events import sanitize_progress_event, should_forward_log


class TestProgressEvents(unittest.TestCase):
    def test_drop_character_portrait_artifact(self):
        event = {
            "type": "artifact",
            "stage": "character_portraits",
            "file_type": "image",
            "file_path": "characters/0/front.png",
        }
        self.assertIsNone(sanitize_progress_event(event))

    def test_convert_frame_artifact_to_progress(self):
        event = {
            "type": "artifact",
            "stage": "frames",
            "file_type": "image",
            "file_path": "shots/0/first_frame.png",
            "shot_idx": 0,
            "frame_type": "first_frame",
        }
        sanitized = sanitize_progress_event(event)
        self.assertEqual(sanitized["type"], "progress")
        self.assertEqual(sanitized["stage"], "frames")

    def test_keep_final_video_artifact(self):
        event = {
            "type": "artifact",
            "stage": "concatenate",
            "file_type": "video",
            "file_path": "final_video.mp4",
        }
        self.assertEqual(sanitize_progress_event(event), event)

    def test_filter_noisy_logs(self):
        self.assertFalse(should_forward_log("httpx", "INFO", "HTTP Request: POST https://api.example.com"))
        self.assertTrue(should_forward_log("httpx", "ERROR", "HTTP Request failed"))
        self.assertFalse(should_forward_log("root", "INFO", "Probed shots/0/video.mp4: 1.2 MB"))


if __name__ == "__main__":
    unittest.main()
