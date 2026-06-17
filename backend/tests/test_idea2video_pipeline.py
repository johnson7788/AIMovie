"""Integration tests for Idea2VideoPipeline.

Tests the pipeline end-to-end with mocked external dependencies:
- Chat models (Screenwriter, CharacterExtractor)
- Image/video generators
- Script2VideoPipeline (per-scene processing)

Also verifies that progress events are emitted in correct order and
that concat_videos is called instead of MoviePy.
"""

import asyncio
import importlib
import json
import os
import sys
import types
import unittest
from unittest.mock import patch, MagicMock, AsyncMock, ANY

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---- stub heavy deps before any project imports ----
_STUB_MODULES = [
    "moviepy", "cv2", "scenedetect", "scenedetect.detectors",
    "PIL", "PIL.Image",
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


def _make_character(idx=0, name="Hero", visible=True):
    """Create a minimal valid CharacterInScene for tests."""
    from interfaces import CharacterInScene
    return CharacterInScene(
        idx=idx,
        identifier_in_scene=name,
        is_visible=visible,
        static_features=f"{name} has brown hair and blue eyes.",
        dynamic_features="Wearing a red cape.",
    )


class TestPipelineInit(unittest.TestCase):
    """Test pipeline initialization from config files."""

    @patch("pipelines.idea2video_pipeline.init_chat_model")
    @patch("pipelines.idea2video_pipeline.RenderBackend.from_config")
    def test_init_from_gpugeek_config(self, mock_backend, mock_init):
        """Pipeline should init correctly from idea2video_gpugeek.yaml."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model
        mock_backend.return_value = MagicMock(
            image_generator=MagicMock(), video_generator=MagicMock()
        )

        from pipelines.idea2video_pipeline import Idea2VideoPipeline
        pipeline = Idea2VideoPipeline.init_from_config("configs/idea2video_gpugeek.yaml")

        self.assertIsNotNone(pipeline.chat_model)
        self.assertIsNotNone(pipeline.image_generator)
        self.assertIsNotNone(pipeline.video_generator)
        self.assertTrue(pipeline.working_dir.endswith("idea2video"))

    @patch("pipelines.idea2video_pipeline.init_chat_model")
    @patch("pipelines.idea2video_pipeline.RenderBackend.from_config")
    def test_init_from_default_config(self, mock_backend, mock_init):
        """Pipeline should init correctly from idea2video.yaml."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model
        mock_backend.return_value = MagicMock(
            image_generator=MagicMock(), video_generator=MagicMock()
        )

        from pipelines.idea2video_pipeline import Idea2VideoPipeline
        pipeline = Idea2VideoPipeline.init_from_config("configs/idea2video.yaml")

        self.assertIsNotNone(pipeline.chat_model)
        self.assertIsNotNone(pipeline.image_generator)
        self.assertIsNotNone(pipeline.video_generator)

    @patch("pipelines.script2video_pipeline.init_chat_model")
    @patch("pipelines.script2video_pipeline.RenderBackend.from_config")
    def test_script2video_init_from_gpugeek_config(self, mock_backend, mock_init):
        """Script2VideoPipeline should init from script2video_gpugeek.yaml."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model
        mock_backend.return_value = MagicMock(
            image_generator=MagicMock(), video_generator=MagicMock()
        )

        from pipelines.script2video_pipeline import Script2VideoPipeline
        pipeline = Script2VideoPipeline.init_from_config("configs/script2video_gpugeek.yaml")

        self.assertIsNotNone(pipeline.chat_model)
        self.assertIsNotNone(pipeline.image_generator)
        self.assertIsNotNone(pipeline.video_generator)


class TestPipelineCall(unittest.TestCase):
    """Test the __call__ method of Idea2VideoPipeline with mocked agents."""

    def _make_pipeline(self):
        """Create a pipeline with mocked chat model and generators."""
        from pipelines.idea2video_pipeline import Idea2VideoPipeline

        pipeline = Idea2VideoPipeline(
            chat_model=MagicMock(),
            image_generator=MagicMock(),
            video_generator=MagicMock(),
            working_dir="/tmp/test_idea2video",
        )

        # Mock the agents
        pipeline.screenwriter = MagicMock()
        pipeline.character_extractor = MagicMock()
        pipeline.character_portraits_generator = MagicMock()

        return pipeline

    def _setup_mocks(self, pipeline, story_text="A test story", script_data=None):
        """Mock the pipeline instance methods that __call__ awaits."""
        pipeline.develop_story = AsyncMock(return_value=story_text)
        pipeline.extract_characters = AsyncMock(return_value=[_make_character()])
        pipeline.generate_character_portraits = AsyncMock(return_value={
            "Hero": {"front": {"path": "/tmp/front.png", "description": "Front view"}}
        })
        pipeline.write_script_based_on_story = AsyncMock(
            return_value=script_data or [{"scene": 1}]
        )

    def _mock_scene_video(self, working_dir: str, scene_idx: int = 0) -> str:
        from pathlib import Path

        scene_video = os.path.join(working_dir, f"scene_{scene_idx}", "final_video.mp4")
        Path(scene_video).parent.mkdir(parents=True, exist_ok=True)
        with open(scene_video, "wb") as handle:
            handle.write(b"fake-video")
        return scene_video

    @patch("utils.video.concat_videos")
    @patch("pipelines.idea2video_pipeline.Script2VideoPipeline")
    @patch("os.makedirs")
    def test_call_emits_stage_events_in_correct_order(self, mock_makedirs, MockS2V, mock_concat):
        """Pipeline should emit stage_start -> artifact -> stage_end in order."""
        from interfaces import CharacterInScene

        pipeline = self._make_pipeline()
        pipeline.working_dir = "/tmp/test_idea2video/test_hash"

        # Mock pipeline methods that __call__ awaits
        pipeline.develop_story = AsyncMock(return_value="A test story")
        pipeline.extract_characters = AsyncMock(return_value=[
            _make_character()
        ])
        pipeline.generate_character_portraits = AsyncMock(return_value={
            "Hero": {"front": {"path": "/tmp/front.png", "description": "Front view"}}
        })
        pipeline.write_script_based_on_story = AsyncMock(
            return_value=[{"scene": 1}, {"scene": 2}]
        )

        # Mock Script2VideoPipeline
        mock_s2v_instance = AsyncMock(return_value="/tmp/scene_0/final_video.mp4")
        MockS2V.return_value = mock_s2v_instance

        events = []

        async def progress_callback(event):
            events.append(dict(event))

        async def run():
            await pipeline(
                idea="A test idea",
                user_requirement="Make it good",
                style="storybook",
                episode_count=2,
                episode_duration=10,
                progress_callback=progress_callback,
            )

        asyncio.run(run())

        # Verify event types
        event_types = [e["type"] for e in events]
        self.assertIn("stage_start", event_types)
        self.assertIn("artifact", event_types)
        self.assertIn("stage_end", event_types)

        # Check text and json artifacts exist
        text_artifacts = [e for e in events if e.get("file_type") == "text"]
        self.assertGreaterEqual(len(text_artifacts), 1)
        json_artifacts = [e for e in events if e.get("file_type") == "json"]
        self.assertGreaterEqual(len(json_artifacts), 2)

        # Verify all expected stages
        stage_names = {e["stage"] for e in events if "stage" in e}
        for s in ["story", "characters", "character_portraits", "script", "concatenate"]:
            self.assertIn(s, stage_names, f"Missing stage: {s}")

    @patch("utils.video.concat_videos")
    @patch("pipelines.idea2video_pipeline.Script2VideoPipeline")
    @patch("os.makedirs")
    def test_artifacts_have_content_preview(self, mock_makedirs, MockS2V, mock_concat):
        """JSON and text artifacts should include content_preview."""
        pipeline = self._make_pipeline()
        pipeline.working_dir = "/tmp/test_idea2video/test_hash"

        story_text = "Once upon a time, there was a hero who saved the world."
        script_data = [{"scene": 1, "description": "Opening scene"}]
        self._setup_mocks(pipeline, story_text=story_text, script_data=script_data)

        scene_video = self._mock_scene_video(pipeline.working_dir)
        mock_s2v_instance = AsyncMock(return_value=scene_video)
        MockS2V.return_value = mock_s2v_instance

        events = []

        async def cb(e):
            events.append(dict(e))

        async def run():
            await pipeline(
                idea="test", user_requirement="test", style="test",
                episode_count=1, progress_callback=cb,
            )

        asyncio.run(run())

        # story.txt
        story_artifact = next(
            (e for e in events if e.get("file_path") == "story.txt"), None
        )
        self.assertIsNotNone(story_artifact)
        self.assertIn("content_preview", story_artifact)
        self.assertIn(story_text[:50], story_artifact["content_preview"])

        # characters.json
        char_artifact = next(
            (e for e in events if e.get("file_path") == "characters.json"), None
        )
        self.assertIsNotNone(char_artifact)
        self.assertIn("content_preview", char_artifact)
        self.assertIn("Hero", char_artifact["content_preview"])

        # script.json
        script_artifact = next(
            (e for e in events if e.get("file_path") == "script.json"), None
        )
        self.assertIsNotNone(script_artifact)
        self.assertIn("content_preview", script_artifact)
        self.assertIn("Opening scene", script_artifact["content_preview"])

    @patch("utils.video.concat_videos")
    @patch("pipelines.idea2video_pipeline.Script2VideoPipeline")
    @patch("os.makedirs")
    def test_uses_concat_videos_not_moviepy(self, mock_makedirs, MockS2V, mock_concat):
        """Multi-scene final output should use concat_videos (ffmpeg), not MoviePy."""
        pipeline = self._make_pipeline()
        pipeline.working_dir = "/tmp/test_idea2video/test_hash"
        self._setup_mocks(pipeline, script_data=[{"scene": 1}, {"scene": 2}])

        scene_videos = [
            self._mock_scene_video(pipeline.working_dir, 0),
            self._mock_scene_video(pipeline.working_dir, 1),
        ]
        mock_s2v_instance = AsyncMock(side_effect=scene_videos)
        MockS2V.return_value = mock_s2v_instance

        async def run():
            await pipeline(
                idea="test", user_requirement="test", style="test",
                episode_count=2, episode_duration=10, progress_callback=AsyncMock(),
            )

        asyncio.run(run())

        mock_concat.assert_called_once()
        call_args = mock_concat.call_args[0]
        video_paths = call_args[0]
        self.assertEqual(len(video_paths), 2)
        self.assertIn("final_video.mp4", video_paths[0])

    @patch("utils.video.concat_videos")
    @patch("pipelines.idea2video_pipeline.Script2VideoPipeline")
    @patch("os.makedirs")
    def test_single_scene_skips_concat(self, mock_makedirs, MockS2V, mock_concat):
        pipeline = self._make_pipeline()
        pipeline.working_dir = "/tmp/test_idea2video/test_hash"
        self._setup_mocks(pipeline)

        scene_video = self._mock_scene_video(pipeline.working_dir)
        mock_s2v_instance = AsyncMock(return_value=scene_video)
        MockS2V.return_value = mock_s2v_instance

        async def run():
            await pipeline(
                idea="test", user_requirement="test", style="test",
                episode_count=1, episode_duration=5, progress_callback=AsyncMock(),
            )

        asyncio.run(run())

        mock_concat.assert_not_called()

    @patch("utils.video.concat_videos")
    @patch("pipelines.idea2video_pipeline.Script2VideoPipeline")
    @patch("os.makedirs")
    def test_scoped_callback_prepends_scene_dir(self, mock_makedirs, MockS2V, mock_concat):
        """Shot artifacts from Script2VideoPipeline should get scene_X/ prefix."""
        pipeline = self._make_pipeline()
        pipeline.working_dir = "/tmp/test_idea2video/test_hash"
        self._setup_mocks(pipeline)

        scene_video = self._mock_scene_video(pipeline.working_dir)

        # Script2VideoPipeline mock: emit shot artifact through callback, then return path
        async def fake_s2v(**kwargs):
            cb = kwargs.get("progress_callback")
            if cb:
                await cb({
                    "type": "artifact", "stage": "frames", "file_type": "image",
                    "file_path": "shots/0/first_frame.png",
                    "shot_idx": 0, "frame_type": "first_frame",
                })
            return scene_video

        mock_s2v_instance = AsyncMock(side_effect=fake_s2v)
        MockS2V.return_value = mock_s2v_instance

        events = []

        async def cb(e):
            events.append(dict(e))

        async def run():
            await pipeline(
                idea="test", user_requirement="test", style="test",
                episode_count=1, progress_callback=cb,
            )

        asyncio.run(run())

        # Find the shot artifact
        shot_artifacts = [
            e for e in events
            if e.get("type") == "artifact" and "shots" in e.get("file_path", "")
        ]
        self.assertGreaterEqual(len(shot_artifacts), 1)

        # The scoped callback should have prepended scene_0/
        shot_path = shot_artifacts[0]["file_path"]
        self.assertTrue(
            shot_path.startswith("scene_0/"),
            f"Expected scene_0/ prefix, got: {shot_path}"
        )


class TestProgressManager(unittest.TestCase):
    """Test the singleton ProgressManager for event publishing."""

    def test_emit_and_get_events(self):
        from progress_manager import ProgressManager
        ProgressManager._instance = None
        pm = ProgressManager.get_instance()

        pm.emit("task-1", {"type": "stage_start", "stage": "story"})
        pm.emit("task-1", {"type": "artifact", "file_path": "story.txt"})
        pm.emit("task-1", {"type": "stage_end", "stage": "story"})

        events = pm.get_events("task-1")
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["type"], "stage_start")
        self.assertEqual(events[1]["type"], "artifact")
        self.assertEqual(events[2]["type"], "stage_end")

    def test_complete_marks_terminal(self):
        from progress_manager import ProgressManager
        ProgressManager._instance = None
        pm = ProgressManager.get_instance()

        self.assertFalse(pm.is_completed("task-2"))
        pm.emit("task-2", {"type": "complete", "result": "/tmp/output.mp4"})
        self.assertTrue(pm.is_completed("task-2"))

    def test_error_marks_terminal(self):
        from progress_manager import ProgressManager
        ProgressManager._instance = None
        pm = ProgressManager.get_instance()

        self.assertFalse(pm.is_completed("task-3"))
        pm.emit("task-3", {"type": "error", "error": "Something failed"})
        self.assertTrue(pm.is_completed("task-3"))

    def test_working_dir_tracking(self):
        from progress_manager import ProgressManager
        ProgressManager._instance = None
        pm = ProgressManager.get_instance()

        pm.set_working_dir("task-4", "/tmp/work/task-4")
        self.assertEqual(pm.get_working_dir("task-4"), "/tmp/work/task-4")
        self.assertIsNone(pm.get_working_dir("nonexistent"))

    def test_events_have_timestamps(self):
        from progress_manager import ProgressManager
        ProgressManager._instance = None
        pm = ProgressManager.get_instance()

        pm.emit("task-5", {"type": "log", "message": "hello"})
        events = pm.get_events("task-5")
        self.assertIn("timestamp", events[0])
        self.assertIsInstance(events[0]["timestamp"], float)


class TestBuildEffectiveUserRequirement(unittest.TestCase):
    def test_includes_original_content_guardrail(self):
        from pipelines.idea2video_pipeline import build_effective_user_requirement

        result = build_effective_user_requirement("做一个短剧", episode_count=1, episode_duration=15)
        self.assertIn("原创虚构角色与场景", result)
        self.assertIn("避免模仿知名影视或宗教地标", result)

    def test_five_second_duration_requests_single_shot(self):
        from pipelines.idea2video_pipeline import build_effective_user_requirement

        result = build_effective_user_requirement("", episode_count=1, episode_duration=5)
        self.assertIn("Use at most 1 shots", result)
        self.assertIn("Use exactly ONE shot", result)
        self.assertNotIn("Prefer 2-3 shots", result)
        self.assertNotIn("Prefer 3 shots", result)


if __name__ == "__main__":
    unittest.main()
