import os
import re
import shutil
import json
import logging
import asyncio
import time
from typing import Optional, Dict, List, Tuple, Literal, Callable, Awaitable

from PIL import Image
from agents import *
import yaml
from interfaces import *
from langchain.chat_models import init_chat_model
from tools.render_backend import RenderBackend
from utils.provider_presets import resolve_chat_model_config
from utils.image import image_output_to_pil, crop_turnaround_views
from utils.seedance_prompt import build_seedance_video_prompt
from utils.pipeline_media import (
    concat_dimensions_for_aspect,
    frame_image_size_for_resolution,
    portrait_turnaround_size,
    portrait_view_size,
    resolve_max_shots_for_duration,
    scene_image_size_for_aspect,
    resolve_aspect_ratio,
    seedance_shot_duration,
    SEEDANCE_SINGLE_CLIP_MAX_SECONDS,
    video_short_side_for_resolution,
)
from utils.pipeline_consistency import (
    build_crossfade_schedule,
    prev_shot_end_reference_text,
    resolve_shot_end_reference,
    scene_anchor_prompt,
    scene_anchor_reference_text,
    should_use_serial_keyframe_pipeline,
    video_last_frame_path,
)
from utils.style_prompts import expand_style_prompt, expand_video_style_prompt
from utils.video import extract_last_frame_from_video
from utils.video import ensure_valid_cached_video
from agents.best_image_selector import BestImageSelector
from agents.screenwriter import Screenwriter

async def _noop_progress(_event):
    pass


def _max_shots_from_user_requirement(user_requirement: str) -> Optional[int]:
    match = re.search(r"Use at most (\d+) shots", user_requirement or "")
    return int(match.group(1)) if match else None


def resolve_max_shots(user_requirement: str = "", episode_duration: int = 0) -> Optional[int]:
    """Derive the hard shot cap from explicit duration or prompt text."""
    if episode_duration > 0:
        return resolve_max_shots_for_duration(episode_duration)
    parsed = _max_shots_from_user_requirement(user_requirement)
    if parsed is not None:
        return parsed
    duration = _episode_duration_from_user_requirement(user_requirement)
    if duration is not None:
        return resolve_max_shots_for_duration(duration)
    return None


def _cleanup_stale_shot_dirs(working_dir: str, allowed_shot_idxs: set[int]) -> bool:
    shots_root = os.path.join(working_dir, "shots")
    if not os.path.isdir(shots_root):
        return False
    removed_any = False
    for name in os.listdir(shots_root):
        if not name.isdigit():
            continue
        shot_idx = int(name)
        if shot_idx not in allowed_shot_idxs:
            stale_dir = os.path.join(shots_root, name)
            shutil.rmtree(stale_dir, ignore_errors=True)
            removed_any = True
            logging.info("Removed stale cached shot directory: %s", stale_dir)
    return removed_any


def _invalidate_final_video_cache(working_dir: str) -> None:
    final_video_path = os.path.join(working_dir, "final_video.mp4")
    if os.path.exists(final_video_path):
        os.remove(final_video_path)
        logging.info("Removed stale final_video.mp4 cache at %s", final_video_path)


def _episode_duration_from_user_requirement(user_requirement: str) -> Optional[int]:
    text = user_requirement or ""
    match = re.search(r"Episode duration: (\d+)s", text)
    if match:
        return int(match.group(1))
    match = re.search(r"Target episode duration: approximately (\d+) seconds", text)
    return int(match.group(1)) if match else None


def _effective_episode_duration(user_requirement: str, episode_duration: int = 0) -> int:
    """Prefer explicit UI duration over text embedded in user_requirement."""
    if episode_duration > 0:
        return episode_duration
    parsed = _episode_duration_from_user_requirement(user_requirement)
    return parsed or 0


def _shot_duration_from_user_requirement(
    user_requirement: str,
    shot_count: int,
    episode_duration: int = 0,
) -> int:
    """Pick Seedance-supported duration (4/5/10/15s) for the target clip."""
    total = _effective_episode_duration(user_requirement, episode_duration)
    return seedance_shot_duration(total, shot_count)


def _image_mse(path_a: str, path_b: str, size: Tuple[int, int] = (64, 64)) -> Optional[float]:
    try:
        image_a = Image.open(path_a).convert("RGB").resize(size)
        image_b = Image.open(path_b).convert("RGB").resize(size)
        pixels_a = list(image_a.getdata())
        pixels_b = list(image_b.getdata())
        return sum(
            sum((left - right) ** 2 for left, right in zip(pixel_a, pixel_b)) / 3
            for pixel_a, pixel_b in zip(pixels_a, pixels_b)
        ) / len(pixels_a)
    except Exception as exc:
        logging.debug("Could not compare continuity images %s and %s: %s", path_a, path_b, exc)
        return None


def _images_are_nearly_identical(path_a: str, path_b: str, threshold: float = 1.0) -> bool:
    mse = _image_mse(path_a, path_b)
    return mse is not None and mse <= threshold


def _should_skip_shot_concat(
    user_requirement: str,
    shot_count: int,
    episode_duration: int = 0,
) -> bool:
    """≤15s single Seedance clip or one shot — no ffmpeg concat."""
    duration = episode_duration or _episode_duration_from_user_requirement(user_requirement) or 0
    if duration > 0 and duration <= SEEDANCE_SINGLE_CLIP_MAX_SECONDS:
        return True
    return shot_count <= 1


def _finalize_single_shot_video(source_path: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if os.path.abspath(source_path) == os.path.abspath(output_path):
        return
    shutil.copy2(source_path, output_path)


def _safe_last_frame_description(frame_desc: str) -> str:
    return (
        f"{frame_desc}\n"
        "For the final frame, avoid a large frontal human face. Prefer a side profile, "
        "back view, over-the-shoulder angle, hands/object detail, or wider environmental "
        "composition while preserving the same character, wardrobe, location, lighting, "
        "and story continuity."
    )


def _looks_like_brief_idea(script: str) -> bool:
    """Detect one-line creative prompts that are not yet a screenplay."""
    text = script.strip()
    if len(text) < 20:
        return True
    if len(text) > 500:
        return False
    screenplay_markers = (
        "INT.", "EXT.", "SCENE", "场景", "镜头", "【", "——", "---",
        "FADE IN", "CUT TO",
    )
    if any(marker in text for marker in screenplay_markers):
        return False
    if text.count("\n") >= 3:
        return False
    return True


def is_fast_single_clip(episode_duration: int, max_shots: Optional[int]) -> bool:
    """≤15s is one Seedance clip; skip heavy multi-shot prep where safe."""
    return (
        episode_duration > 0
        and episode_duration <= SEEDANCE_SINGLE_CLIP_MAX_SECONDS
        and max_shots == 1
    )


class Script2VideoPipeline:

    # Use turnaround sheet (single image with 3 views) for better character consistency.
    # Set to False to fall back to the old 3-separate-call method.
    USE_TURNAROUND_SHEET = True
    FRAME_CANDIDATE_COUNT = 2

    def __init__(
        self,
        chat_model: str,
        image_generator,
        video_generator,
        working_dir: str,
        multimodal_chat_model=None,
        best_image_selector: Optional[BestImageSelector] = None,
    ):

        self.chat_model = chat_model
        self.image_generator = image_generator
        self.video_generator = video_generator

        self.character_extractor = CharacterExtractor(chat_model=self.chat_model)
        self.character_portraits_generator = CharacterPortraitsGenerator(image_generator=self.image_generator)
        self.storyboard_artist = StoryboardArtist(chat_model=self.chat_model)
        self.screenwriter = Screenwriter(chat_model=self.chat_model)
        self.camera_image_generator = CameraImageGenerator(chat_model=self.chat_model, image_generator=self.image_generator, video_generator=self.video_generator)
        self.reference_image_selector = ReferenceImageSelector(chat_model=self.chat_model, multimodal_model=multimodal_chat_model)
        self.best_image_selector = best_image_selector

        self.character_portrait_events = {}
        self.shot_desc_events = {}
        self.frame_events = {}
        self._scene_anchor_path = ""

        self.working_dir = working_dir
        os.makedirs(self.working_dir, exist_ok=True)



    @classmethod
    def init_from_config(cls, config_path: str, chat_model_override=None, image_generator_override=None, video_generator_override=None):
        config_file = config_path
        if not os.path.isabs(config_path):
            config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                config_path,
            )
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if chat_model_override is not None:
            chat_model = chat_model_override
        else:
            chat_model_args = resolve_chat_model_config(config["chat_model"]["init_args"])
            chat_model = init_chat_model(**chat_model_args)

        multimodal_chat_model = None
        if "multimodal_chat_model" in config:
            multimodal_args = resolve_chat_model_config(config["multimodal_chat_model"]["init_args"])
            multimodal_chat_model = init_chat_model(**multimodal_args)
            print(f"🖼️ Multimodal model for reference selection: {multimodal_args.get('model')}")
        elif chat_model_override is not None:
            print("⚠️ No multimodal_chat_model in config; reference image selection will use text-only fallback.")

        if image_generator_override is not None and video_generator_override is not None:
            image_generator = image_generator_override
            video_generator = video_generator_override
        else:
            backend = RenderBackend.from_config(config)
            image_generator = image_generator_override or backend.image_generator
            video_generator = video_generator_override or backend.video_generator

        best_image_selector = None
        if "multimodal_chat_model" in config:
            multimodal_args = resolve_chat_model_config(config["multimodal_chat_model"]["init_args"])
            if multimodal_args.get("api_key") and multimodal_args.get("base_url") and multimodal_args.get("model"):
                best_image_selector = BestImageSelector(
                    base_url=multimodal_args["base_url"],
                    api_key=multimodal_args["api_key"],
                    chat_model=multimodal_args["model"],
                )

        return cls(
            chat_model=chat_model,
            image_generator=image_generator,
            video_generator=video_generator,
            working_dir=config["working_dir"],
            multimodal_chat_model=multimodal_chat_model,
            best_image_selector=best_image_selector,
        )

    async def __call__(
        self,
        script: str,
        user_requirement: str,
        style: str,
        characters: List[CharacterInScene] = None,
        character_portraits_registry: Optional[Dict[str, Dict[str, Dict[str, str]]]] = None,
        aspect_ratio: str = "",
        resolution: str = "480p",
        episode_duration: int = 0,
        progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        cb = progress_callback or _noop_progress
        self._progress_callback = cb
        self._episode_duration = _effective_episode_duration(user_requirement, episode_duration)
        self._max_shots = resolve_max_shots(user_requirement, self._episode_duration)
        self._fast_single_clip = is_fast_single_clip(self._episode_duration, self._max_shots)
        skip_concat = (
            self._episode_duration <= SEEDANCE_SINGLE_CLIP_MAX_SECONDS
            or self._max_shots == 1
        )
        print(
            f"⏱️ Episode duration: {self._episode_duration}s, "
            f"max_shots={self._max_shots}, skip_concat={skip_concat}, "
            f"seedance_single_clip={self._episode_duration <= SEEDANCE_SINGLE_CLIP_MAX_SECONDS}"
        )
        if skip_concat and not self._fast_single_clip:
            print(
                "ℹ️ skip_concat only skips final ffmpeg merge; script/portraits/frames/video "
                "still run. Restart backend to enable ⚡ fast single-clip optimizations."
            )
        if self._fast_single_clip:
            print(
                f"⚡ Fast single-clip mode (≤{SEEDANCE_SINGLE_CLIP_MAX_SECONDS}s): micro script, "
                "3-view turnaround portraits, skip last frame / extra frame candidates / camera-tree LLM."
            )
        self._aspect_ratio = resolve_aspect_ratio(user_requirement, explicit=aspect_ratio or None)
        self._resolution = resolution or "480p"
        self._scene_image_size = scene_image_size_for_aspect(self._aspect_ratio)
        self._portrait_turnaround_size = portrait_turnaround_size()
        self._portrait_view_size = portrait_view_size()
        self._frame_size = self._scene_image_size
        self._concat_size = concat_dimensions_for_aspect(
            self._aspect_ratio,
            short_side=video_short_side_for_resolution(self._resolution),
        )
        self._style_prompt = expand_style_prompt(style)
        self._video_style_prompt = expand_video_style_prompt(style)
        self._style = style
        self.camera_image_generator.frame_size = self._frame_size
        self.camera_image_generator.aspect_ratio = self._aspect_ratio
        print(
            f"📐 Output aspect ratio: {self._aspect_ratio} "
            f"(portraits={self._portrait_turnaround_size}, "
            f"scene/keyframes={self._scene_image_size}, video={self._resolution}, "
            f"concat={self._concat_size[0]}x{self._concat_size[1]})"
        )

        if characters is None:
            script_path = os.path.join(self.working_dir, "script.txt")
            if os.path.exists(script_path):
                with open(script_path, "r", encoding="utf-8") as f:
                    script = f.read()
                print(f"🚀 Loaded script from {script_path}.")
            elif _looks_like_brief_idea(script):
                await cb({
                    "type": "stage_start",
                    "stage": "script",
                    "message": "Expanding idea into script before character extraction...",
                })
                t0 = time.time()
                if self._fast_single_clip:
                    print("⚡ Fast single-clip mode: writing micro script in one LLM call...")
                    script = await self.screenwriter.write_micro_script_from_idea(
                        idea=script,
                        user_requirement=user_requirement,
                    )
                else:
                    print("📝 Input looks like a brief idea; expanding into script...")
                    story = await self.screenwriter.develop_story(
                        idea=script,
                        user_requirement=user_requirement,
                    )
                    scene_scripts = await self.screenwriter.write_script_based_on_story(
                        story=story,
                        user_requirement=user_requirement,
                    )
                    script = scene_scripts[0] if scene_scripts else story
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script)
                await cb({
                    "type": "artifact",
                    "stage": "script",
                    "file_type": "text",
                    "file_path": "script.txt",
                    "content_preview": script[:500],
                })
                await cb({
                    "type": "stage_end",
                    "stage": "script",
                    "duration_ms": int((time.time() - t0) * 1000),
                })

            await cb({"type": "stage_start", "stage": "characters", "message": "Extracting characters from script..."})
            t0 = time.time()
            characters = await self.extract_characters(script=script)
            await cb({"type": "stage_end", "stage": "characters", "duration_ms": int((time.time() - t0) * 1000)})

        if character_portraits_registry is None:
            character_portraits_registry_path = os.path.join(self.working_dir, "character_portraits_registry.json")
            if os.path.exists(character_portraits_registry_path):
                with open(character_portraits_registry_path, "r", encoding="utf-8") as f:
                    character_portraits_registry = json.load(f)
                print(f"🚀 Loaded {len(character_portraits_registry)} character portraits from existing file.")
                await cb({
                    "type": "stage_start",
                    "stage": "character_portraits",
                    "message": f"Loaded {len(character_portraits_registry)} character portrait set(s) from cache.",
                })
                await self._emit_character_portrait_artifacts(character_portraits_registry, cb)
                await cb({"type": "stage_end", "stage": "character_portraits", "duration_ms": 0})
            else:
                await cb({"type": "stage_start", "stage": "character_portraits", "message": "Generating character portraits..."})
                t0 = time.time()
                print(f"🔍 Generating character portraits...")
                character_portraits_registry = await self.generate_character_portraits(
                    characters=characters,
                    character_portraits_registry=None,
                    style=style,
                )

                with open(character_portraits_registry_path, "w", encoding="utf-8") as f:
                    json.dump(character_portraits_registry, f, ensure_ascii=False, indent=4)
                print(f"☑️ Generated {len(character_portraits_registry)} character portraits and saved to {character_portraits_registry_path}.")
                await cb({"type": "stage_end", "stage": "character_portraits", "duration_ms": int((time.time() - t0) * 1000)})

        # design shots
        await cb({"type": "stage_start", "stage": "storyboard", "message": "Designing storyboard..."})
        t0 = time.time()
        storyboard = await self.design_storyboard(
            script=script,
            characters=characters,
            user_requirement=user_requirement,
            episode_duration=self._episode_duration,
        )
        await cb({"type": "stage_end", "stage": "storyboard", "duration_ms": int((time.time() - t0) * 1000), "shot_count": len(storyboard)})

        # decompose visual descriptions of shots
        await cb({"type": "stage_start", "stage": "visual_descriptions", "message": f"Decomposing visual descriptions for {len(storyboard)} shots..."})
        t0 = time.time()
        shot_descriptions = await self.decompose_visual_descriptions(
            shot_brief_descriptions=storyboard,
            characters=characters,
        )
        await cb({"type": "stage_end", "stage": "visual_descriptions", "duration_ms": int((time.time() - t0) * 1000)})

        if self._fast_single_clip:
            for shot_description in shot_descriptions:
                shot_description.variation_type = "small"

        await cb({"type": "stage_start", "stage": "scene_anchor", "message": "Generating scene establishing anchor..."})
        t0 = time.time()
        self._scene_anchor_path = await self.generate_scene_anchor(script=script)
        await cb({"type": "stage_end", "stage": "scene_anchor", "duration_ms": int((time.time() - t0) * 1000)})

        self._shot_duration = _shot_duration_from_user_requirement(
            user_requirement, len(shot_descriptions), self._episode_duration
        )
        target_episode = self._episode_duration
        if target_episode:
            print(
                f"⏱️ Per-shot video duration: {self._shot_duration}s "
                f"(target episode ~{target_episode}s, {len(shot_descriptions)} shots)"
            )

        # construct camera tree
        await cb({"type": "stage_start", "stage": "camera_tree", "message": "Constructing camera tree..."})
        t0 = time.time()
        camera_tree = await self.construct_camera_tree(
            shot_descriptions=shot_descriptions,
        )
        await cb({"type": "stage_end", "stage": "camera_tree", "duration_ms": int((time.time() - t0) * 1000)})

        priority_shot_idxs = [camera.parent_cam_idx for camera in camera_tree if camera.parent_cam_idx is not None]
        total_shots = len(shot_descriptions)
        use_serial_keyframe = should_use_serial_keyframe_pipeline(camera_tree, user_requirement)
        print(f"📋 Processing {total_shots} shots across {len(camera_tree)} camera(s)...")
        mode_label = "serial keyframe" if use_serial_keyframe else "parallel frames + serial videos"
        await cb({
            "type": "stage_start",
            "stage": "frames",
            "message": f"Generating frames/videos for {total_shots} shots ({mode_label})...",
        })
        t0 = time.time()
        if use_serial_keyframe:
            await self.generate_shots_serial_keyframe(
                shot_descriptions=shot_descriptions,
                characters=characters,
                character_portraits_registry=character_portraits_registry,
                camera_tree=camera_tree,
            )
        else:
            tasks = [
                self.generate_frames_for_single_camera(
                    camera=camera,
                    shot_descriptions=shot_descriptions,
                    characters=characters,
                    character_portraits_registry=character_portraits_registry,
                    priority_shot_idxs=priority_shot_idxs,
                )
                for camera in camera_tree
            ]
            await asyncio.gather(*tasks)
            await cb({"type": "stage_start", "stage": "videos", "message": f"Generating videos for {total_shots} shots sequentially..."})
            t_video = time.time()
            await self.generate_videos_in_order(shot_descriptions=shot_descriptions)
            await cb({"type": "stage_end", "stage": "videos", "duration_ms": int((time.time() - t_video) * 1000)})
        await cb({"type": "stage_end", "stage": "frames", "duration_ms": int((time.time() - t0) * 1000)})

        final_video_path = os.path.join(self.working_dir, "final_video.mp4")
        shot_video_paths = [
            os.path.join(self.working_dir, "shots", f"{shot_description.idx}", "video.mp4")
            for shot_description in shot_descriptions
        ]
        skip_concat = _should_skip_shot_concat(
            user_requirement,
            len(shot_descriptions),
            self._episode_duration,
        )
        if ensure_valid_cached_video(final_video_path, "scene final video"):
            print(f"🚀 Skipped concatenating videos, already exists.")
        elif skip_concat:
            source_video = shot_video_paths[0]
            if not os.path.exists(source_video):
                raise FileNotFoundError(f"Single-shot video not found: {source_video}")
            await cb({
                "type": "stage_start",
                "stage": "concatenate",
                "message": "Using single generated clip (no concat)...",
            })
            t0 = time.time()
            print(f"🎬 Single {len(shot_descriptions)}-shot clip; copying to {final_video_path}...")
            _finalize_single_shot_video(source_video, final_video_path)
            print(f"☑️ Saved final video to {final_video_path}.")
            await cb({"type": "stage_end", "stage": "concatenate", "duration_ms": int((time.time() - t0) * 1000)})
        else:
            await cb({"type": "stage_start", "stage": "concatenate", "message": "Concatenating shot videos..."})
            t0 = time.time()
            print(f"🎬 Starting concatenating videos...")
            from utils.video import concat_videos
            width, height = self._concat_size
            crossfade_schedule = build_crossfade_schedule(shot_descriptions)
            concat_videos(
                shot_video_paths,
                final_video_path,
                target_width=width,
                target_height=height,
                crossfade_seconds=crossfade_schedule if crossfade_schedule else 0.0,
            )
            print(f"☑️ Concatenated videos, saved to {final_video_path}.")
            await cb({"type": "stage_end", "stage": "concatenate", "duration_ms": int((time.time() - t0) * 1000)})

        await cb({
            "type": "artifact", "stage": "concatenate", "file_type": "video",
            "file_path": "final_video.mp4",
        })

        self._progress_callback = None
        return final_video_path

    def _portrait_image_gen_kwargs(self, *, turnaround: bool = False) -> dict:
        return {
            "size": self._portrait_turnaround_size if turnaround else self._portrait_view_size,
        }

    def _scene_image_gen_kwargs(self) -> dict:
        """Scene anchor and shot keyframes (Seedream API minimum for aspect ratio)."""
        return {"size": self._scene_image_size}

    def _frame_image_gen_kwargs(self) -> dict:
        return self._scene_image_gen_kwargs()

    def _frame_candidate_count(self) -> int:
        if getattr(self, "_fast_single_clip", False):
            return 1
        if (getattr(self, "_resolution", "480p") or "480p").lower() == "480p":
            return 1
        return self.FRAME_CANDIDATE_COUNT if self.best_image_selector else 1

    def _scene_anchor_pair(self) -> Tuple[str, str]:
        return (self._scene_anchor_path, scene_anchor_reference_text())

    async def generate_scene_anchor(self, script: str) -> str:
        anchor_path = os.path.join(self.working_dir, "scene_anchor.png")
        if os.path.exists(anchor_path):
            print("🚀 Loaded existing scene anchor image.")
            return anchor_path

        print("🏞️ Generating scene establishing anchor (empty environment)...")
        prompt = scene_anchor_prompt(script, self._style_prompt)
        anchor_image = await self.image_generator.generate_single_image(
            prompt=prompt,
            reference_image_paths=[],
            **self._frame_image_gen_kwargs(),
        )
        anchor_image.save(anchor_path)
        print(f"☑️ Scene anchor saved to {anchor_path}.")
        cb = getattr(self, "_progress_callback", None)
        if cb:
            await cb({
                "type": "artifact",
                "stage": "scene_anchor",
                "file_type": "image",
                "file_path": "scene_anchor.png",
            })
        return anchor_path

    async def _save_generated_frame(
        self,
        frame_image_path: str,
        prompt: str,
        reference_image_paths: List[str],
        reference_image_path_and_text_pairs: List[Tuple[str, str]],
        target_description: str,
    ) -> None:
        candidate_count = self._frame_candidate_count()
        candidates_dir = os.path.join(os.path.dirname(frame_image_path), "candidates")
        os.makedirs(candidates_dir, exist_ok=True)
        candidate_paths: List[str] = []

        for index in range(candidate_count):
            candidate_path = os.path.join(candidates_dir, f"{index}.png")
            if not (candidate_count == 1 and os.path.exists(frame_image_path) and index == 0):
                frame_image = await self.image_generator.generate_single_image(
                    prompt=prompt,
                    reference_image_paths=reference_image_paths,
                    **self._frame_image_gen_kwargs(),
                )
                frame_image.save(candidate_path)
            elif os.path.exists(frame_image_path):
                shutil.copy(frame_image_path, candidate_path)
            candidate_paths.append(candidate_path)

        if self.best_image_selector and len(candidate_paths) > 1:
            try:
                best_path = await self.best_image_selector(
                    reference_image_path_and_text_pairs=reference_image_path_and_text_pairs,
                    target_description=target_description,
                    candidate_image_paths=candidate_paths,
                )
                shutil.copy(best_path, frame_image_path)
                return
            except Exception as exc:
                logging.warning(
                    "BestImageSelector failed for %s, using first candidate: %s",
                    frame_image_path,
                    exc,
                )

        shutil.copy(candidate_paths[0], frame_image_path)

    def _build_video_reference_paths(
        self,
        shot_description: ShotDescription,
        prev_shot_last_frame_path: Optional[str],
    ) -> List[str]:
        first_frame_path = os.path.join(
            self.working_dir, "shots", f"{shot_description.idx}", "first_frame.png"
        )
        scene_anchor = (
            self._scene_anchor_path
            if self._scene_anchor_path and os.path.exists(self._scene_anchor_path)
            else None
        )
        if (
            shot_description.idx > 0
            and prev_shot_last_frame_path
            and os.path.exists(prev_shot_last_frame_path)
            and os.path.exists(first_frame_path)
        ):
            mse = _image_mse(prev_shot_last_frame_path, first_frame_path)
            if mse is not None:
                log = logging.warning if mse > 1500 else logging.info
                log(
                    "Continuity check shot %s: prev video tail vs current first_frame MSE=%.1f",
                    shot_description.idx,
                    mse,
                )

        if (
            shot_description.idx > 0
            and prev_shot_last_frame_path
            and os.path.exists(prev_shot_last_frame_path)
        ):
            # In serial handoff mode the current first_frame is copied from the previous
            # video's true tail. Prefer a single first-frame reference for Seedance:
            # independently generated last-frame targets can make the model morph into
            # a different person or scene.
            if os.path.exists(first_frame_path) and _images_are_nearly_identical(
                first_frame_path,
                prev_shot_last_frame_path,
            ):
                refs = [first_frame_path]
                self._log_video_reference_paths(shot_description, refs)
                return refs
            refs = [prev_shot_last_frame_path, first_frame_path][:2]
            self._log_video_reference_paths(shot_description, refs)
            return refs

        if shot_description.variation_type in ["medium", "large"]:
            last_frame_path = os.path.join(
                self.working_dir, "shots", f"{shot_description.idx}", "last_frame.png"
            )
            if os.path.exists(last_frame_path):
                refs = [first_frame_path, last_frame_path][:2]
                self._log_video_reference_paths(shot_description, refs)
                return refs

        if scene_anchor:
            refs = [scene_anchor, first_frame_path][:2]
            self._log_video_reference_paths(shot_description, refs)
            return refs

        refs = [first_frame_path]
        self._log_video_reference_paths(shot_description, refs)
        return refs

    def _log_video_reference_paths(
        self,
        shot_description: ShotDescription,
        frame_paths: List[str],
    ) -> None:
        logging.info(
            "Shot %s video references (%s): %s",
            shot_description.idx,
            shot_description.variation_type,
            [os.path.relpath(path, self.working_dir) for path in frame_paths],
        )

    def _resolve_shot_end_reference(
        self,
        shot_idx: int,
        video_path: str,
        api_last_frame_url: Optional[str] = None,
    ) -> Optional[str]:
        return resolve_shot_end_reference(
            self.working_dir,
            shot_idx,
            video_path,
            extract_last_frame_from_video,
            api_last_frame_url=api_last_frame_url,
        )

    async def generate_shots_serial_keyframe(
        self,
        shot_descriptions: List[ShotDescription],
        characters: List[CharacterInScene],
        character_portraits_registry: Dict[str, Dict[str, Dict[str, str]]],
        camera_tree: List[Camera],
    ) -> None:
        """Generate each shot in order: first_frame → optional last_frame → video → handoff."""
        prev_handoff_path: Optional[str] = None
        ordered_shots = sorted(shot_descriptions, key=lambda item: item.idx)
        if not ordered_shots:
            return
        shots_by_idx = {shot.idx: shot for shot in shot_descriptions}
        first_shot_idx = ordered_shots[0].idx
        first_shot_ff_path = os.path.join(self.working_dir, "shots", f"{first_shot_idx}", "first_frame.png")
        prev_shot_idx: Optional[int] = None

        await self._emit_progress({
            "type": "stage_start",
            "stage": "videos",
            "message": f"Generating {len(ordered_shots)} shots in serial keyframe order...",
        })
        t_video = time.time()

        for shot_description in ordered_shots:
            shot_idx = shot_description.idx
            prev_end_pair: Optional[Tuple[str, str]] = None
            if prev_handoff_path and os.path.exists(prev_handoff_path) and shot_idx > 0:
                prev_end_pair = (
                    prev_handoff_path,
                    prev_shot_end_reference_text(prev_shot_idx if prev_shot_idx is not None else shot_idx - 1),
                )

            if prev_end_pair:
                self._prepare_soft_handoff_first_frame(shot_idx, prev_end_pair[0])
            await self.generate_frame_for_single_shot(
                shot_idx=shot_idx,
                frame_type="first_frame",
                first_shot_ff_path_and_text_pair=(
                    first_shot_ff_path,
                    shots_by_idx[first_shot_idx].ff_desc,
                ),
                frame_desc=shot_description.ff_desc,
                visible_characters=[characters[idx] for idx in shot_description.ff_vis_char_idxs],
                character_portraits_registry=character_portraits_registry,
                prev_shot_end_reference=prev_end_pair,
            )
            self.frame_events[shot_idx]["first_frame"].set()

            if shot_description.variation_type in ["medium", "large"] and not getattr(self, "_fast_single_clip", False):
                await self.generate_frame_for_single_shot(
                    shot_idx=shot_idx,
                    frame_type="last_frame",
                    first_shot_ff_path_and_text_pair=(
                        first_shot_ff_path,
                        shots_by_idx[first_shot_idx].ff_desc,
                    ),
                    frame_desc=shot_description.lf_desc,
                    visible_characters=[characters[idx] for idx in shot_description.lf_vis_char_idxs],
                    character_portraits_registry=character_portraits_registry,
                    prev_shot_end_reference=prev_end_pair,
                )
                self.frame_events[shot_idx]["last_frame"].set()

            prev_handoff_path = await self.generate_video_for_single_shot(
                shot_description=shot_description,
                prev_shot_last_frame_path=prev_handoff_path,
            )
            prev_shot_idx = shot_idx

        await self._emit_progress({
            "type": "stage_end",
            "stage": "videos",
            "duration_ms": int((time.time() - t_video) * 1000),
        })

    async def _emit_progress(self, event: dict) -> None:
        cb = getattr(self, "_progress_callback", None)
        if cb:
            await cb(event)

    def _prepare_soft_handoff_first_frame(self, shot_idx: int, handoff_path: str) -> None:
        """Regenerate previously forced handoffs through the image model."""
        shot_dir = os.path.join(self.working_dir, "shots", f"{shot_idx}")
        first_frame_path = os.path.join(shot_dir, "first_frame.png")
        selector_output = os.path.join(shot_dir, "first_frame_selector_output.json")
        if not (
            os.path.exists(first_frame_path)
            and os.path.exists(handoff_path)
            and _images_are_nearly_identical(first_frame_path, handoff_path)
            and not os.path.exists(selector_output)
        ):
            return

        os.remove(first_frame_path)
        for stale_name in ("video.mp4", "video_last_frame.png", "video_safe_reference.png"):
            stale_path = os.path.join(shot_dir, stale_name)
            if os.path.exists(stale_path):
                os.remove(stale_path)
        logging.info(
            "Removed old forced shot %s first_frame so image model can regenerate a soft handoff.",
            shot_idx,
        )

    def _force_first_frame_from_handoff(self, shot_idx: int, handoff_path: str) -> None:
        """Make shot N start exactly where shot N-1 video ended."""
        shot_dir = os.path.join(self.working_dir, "shots", f"{shot_idx}")
        os.makedirs(shot_dir, exist_ok=True)
        first_frame_path = os.path.join(shot_dir, "first_frame.png")
        changed = not (
            os.path.exists(first_frame_path)
            and _images_are_nearly_identical(first_frame_path, handoff_path)
        )
        if changed:
            shutil.copy(handoff_path, first_frame_path)
            for stale_name in ("video.mp4", "video_last_frame.png"):
                stale_path = os.path.join(shot_dir, stale_name)
                if os.path.exists(stale_path):
                    os.remove(stale_path)
            selector_output = os.path.join(shot_dir, "first_frame_selector_output.json")
            if os.path.exists(selector_output):
                os.remove(selector_output)
            logging.info(
                "Forced shot %s first_frame from previous video tail and invalidated stale video cache: %s",
                shot_idx,
                first_frame_path,
            )
        else:
            logging.info("Shot %s first_frame already matches previous video tail.", shot_idx)

    async def _rewrite_rejected_video_reference(
        self,
        shot_description: ShotDescription,
        rejected_paths: List[str],
        error: str,
    ) -> List[str]:
        if not rejected_paths:
            return []

        shot_dir = os.path.join(self.working_dir, "shots", f"{shot_description.idx}")
        os.makedirs(shot_dir, exist_ok=True)
        source_path = rejected_paths[0]
        safe_path = os.path.join(shot_dir, "video_safe_reference.png")
        prompt = (
            "Create a moderation-safe AI video first-frame reference based on Image 0. "
            "Preserve the same fictional character identity, wardrobe, location, props, "
            "lighting, camera continuity, and action setup, but reduce real-person risk: "
            "avoid a large frontal face, celebrity likeness, passport/photo/headshot look, "
            "selfie, or news-photo realism. Prefer a side profile, back view, "
            "over-the-shoulder view, hands/object detail, or slightly wider film still. "
            "The result must be clearly a fictional AI-generated movie frame and still "
            "usable as the next clip's first frame."
        )
        logging.warning(
            "Rewriting rejected video reference for shot %s with image model: %s; error=%s",
            shot_description.idx,
            source_path,
            error,
        )
        safe_image = await self.image_generator.generate_single_image(
            prompt=prompt,
            reference_image_paths=[source_path],
            **self._frame_image_gen_kwargs(),
        )
        safe_image.save(safe_path)
        logging.info(
            "Saved moderation-safe video reference for shot %s: %s",
            shot_description.idx,
            safe_path,
        )
        return [safe_path]

    async def generate_videos_in_order(
        self,
        shot_descriptions: List[ShotDescription],
    ) -> None:
        prev_last_frame_path: Optional[str] = None
        ordered_shots = sorted(shot_descriptions, key=lambda item: item.idx)
        for shot_description in ordered_shots:
            prev_last_frame_path = await self.generate_video_for_single_shot(
                shot_description=shot_description,
                prev_shot_last_frame_path=prev_last_frame_path,
            )


    async def generate_frames_for_single_camera(
        self,
        camera: Camera,
        shot_descriptions: List[ShotDescription],
        characters: List[CharacterInScene],
        character_portraits_registry: Dict[str, Dict[str, Dict[str, str]]],
        priority_shot_idxs: List[int],
    ):
        # 1. generate the first_frame of the first shot of the camera
        first_shot_idx = camera.active_shot_idxs[0]
        first_shot_ff_path = os.path.join(self.working_dir, "shots", f"{first_shot_idx}", "first_frame.png")

        if os.path.exists(first_shot_ff_path):
            print(f"🚀 Skipped generating first_frame for shot {first_shot_idx}, already exists.")
            self.frame_events[first_shot_idx]["first_frame"].set()

        else:
            print(f"🖼️ Starting first_frame generation for shot {first_shot_idx}...")
            available_image_path_and_text_pairs = []
            if self._scene_anchor_path and os.path.exists(self._scene_anchor_path):
                available_image_path_and_text_pairs.append(self._scene_anchor_pair())

            for character_idx in shot_descriptions[first_shot_idx].ff_vis_char_idxs:
                identifier_in_scene = characters[character_idx].identifier_in_scene
                registry_item = character_portraits_registry[identifier_in_scene]
                for view, item in registry_item.items():
                    available_image_path_and_text_pairs.append((item["path"], item["description"]))
            
            # generate the first_frame based on the shot_description.ff_desc
            if camera.parent_shot_idx is not None:
                # generate the first_frame based on the transition video
                parent_shot_idx = camera.parent_shot_idx
                await self.frame_events[parent_shot_idx]["first_frame"].wait()
                parent_shot_ff_path = os.path.join(self.working_dir, "shots", f"{parent_shot_idx}", "first_frame.png")
                transition_video_path = os.path.join(self.working_dir, "shots", f"{first_shot_idx}", f"transition_video_from_shot_{parent_shot_idx}.mp4")

                if os.path.exists(transition_video_path):
                    print(f"🚀 Skipped generating transition video for shot {first_shot_idx} from shot {parent_shot_idx}, already exists.")
                else:
                    print(f"🖼️ Starting transition video generation for shot {first_shot_idx} from shot {parent_shot_idx}...")
                    transition_video_output = await self.camera_image_generator.generate_transition_video(
                        first_shot_visual_desc=shot_descriptions[parent_shot_idx].visual_desc,
                        second_shot_visual_desc=shot_descriptions[first_shot_idx].visual_desc,
                        first_shot_ff_path=parent_shot_ff_path,
                    )
                    transition_video_output.save(transition_video_path)
                    print(f"☑️ Generated transition video for shot {first_shot_idx} from shot {parent_shot_idx}, saved to {transition_video_path}.")

                new_camera_image_path = os.path.join(self.working_dir, "shots", f"{first_shot_idx}", f"new_camera_{camera.idx}.png")
                if os.path.exists(new_camera_image_path):
                    print(f"🚀 Skipped generating new camera image for shot {first_shot_idx}, already exists.")
                else:
                    print(f"🖼️ Starting new camera image generation for shot {first_shot_idx}...")
                    new_camera_image = self.camera_image_generator.get_new_camera_image(transition_video_path)
                    new_camera_image.save(new_camera_image_path)
                    print(f"☑️ Generated new camera image for shot {first_shot_idx} (not completed), saved to {new_camera_image_path}.")

                    available_image_path_and_text_pairs.append(
                        (
                            new_camera_image_path,
                            f"The composition and background are correct but some elements may be wrong. The wrong elements should be replaced.\nWrong elements: {camera.missing_info}.\nYou must select this image as the main reference and replace the characters in the image with the provided character portraits. Don't change the background."
                        )
                    )


            # 如果子镜头缺少信息，则需要选择参考图像生成
            if camera.parent_shot_idx is None or camera.missing_info is not None:
                ff_selector_output_path = os.path.join(self.working_dir, "shots", f"{first_shot_idx}", "first_frame_selector_output.json")
                if os.path.exists(ff_selector_output_path):
                    with open(ff_selector_output_path, 'r', encoding='utf-8') as f:
                        ff_selector_output = json.load(f)
                    print(f"🚀 Loaded existing reference image selection and prompt for first_frame of shot {first_shot_idx} from {ff_selector_output_path}.")
                else:
                    print(f"🔍 Selecting reference images and generating prompt for first_frame of shot {first_shot_idx}...")
                    ff_selector_output = await self.reference_image_selector.select_reference_images_and_generate_prompt(
                        available_image_path_and_text_pairs=available_image_path_and_text_pairs,
                        frame_description=shot_descriptions[first_shot_idx].ff_desc
                    )
                    with open(ff_selector_output_path, 'w', encoding='utf-8') as f:
                        json.dump(ff_selector_output, f, ensure_ascii=False, indent=4)

                    print(f"☑️ Selected reference images and generated prompt for first_frame of shot {first_shot_idx}, saved to {ff_selector_output_path}.")

                reference_image_path_and_text_pairs, prompt = ff_selector_output["reference_image_path_and_text_pairs"], ff_selector_output["text_prompt"]
                prefix_prompt = ""
                for i, (image_path, text) in enumerate(reference_image_path_and_text_pairs):
                    prefix_prompt += f"Image {i}: {text}\n"
                prompt = f"{prefix_prompt}\n{prompt}\nStyle: {self._style_prompt}"
                reference_image_paths = [item[0] for item in reference_image_path_and_text_pairs]
                await self._save_generated_frame(
                    frame_image_path=first_shot_ff_path,
                    prompt=prompt,
                    reference_image_paths=reference_image_paths,
                    reference_image_path_and_text_pairs=reference_image_path_and_text_pairs,
                    target_description=shot_descriptions[first_shot_idx].ff_desc,
                )
                self.frame_events[first_shot_idx]["first_frame"].set()
                print(f"☑️ Generated first_frame for shot {first_shot_idx}, saved to {first_shot_ff_path}.")
            else:
                shutil.copy(new_camera_image_path, first_shot_ff_path)
                self.frame_events[first_shot_idx]["first_frame"].set()
                print(f"☑️ Generated first_frame for shot {first_shot_idx}, saved to {first_shot_ff_path}.")
            # Emit artifact for first frame
            cb = getattr(self, "_progress_callback", None)
            if cb:
                await cb({
                    "type": "artifact", "stage": "frames", "file_type": "image",
                    "file_path": os.path.join("shots", f"{first_shot_idx}", "first_frame.png"),
                    "shot_idx": first_shot_idx, "frame_type": "first_frame",
                })


        # 2. generate the following frames of the camera
        priority_tasks = []
        normal_tasks = []

        if shot_descriptions[first_shot_idx].variation_type in ["medium", "large"]:
            task = self.generate_frame_for_single_shot(
                shot_idx=first_shot_idx, 
                frame_type="last_frame", 
                first_shot_ff_path_and_text_pair=(first_shot_ff_path, shot_descriptions[first_shot_idx].ff_desc),
                frame_desc=shot_descriptions[first_shot_idx].lf_desc,
                visible_characters=[characters[idx] for idx in shot_descriptions[first_shot_idx].lf_vis_char_idxs],
                character_portraits_registry=character_portraits_registry,
            )
            normal_tasks.append(task)

        for shot_idx in camera.active_shot_idxs[1:]:
            first_frame_task = self.generate_frame_for_single_shot(
                    shot_idx=shot_idx, 
                    frame_type="first_frame", 
                    first_shot_ff_path_and_text_pair=(first_shot_ff_path, shot_descriptions[first_shot_idx].ff_desc),
                    frame_desc=shot_descriptions[shot_idx].ff_desc,
                    visible_characters=[characters[idx] for idx in shot_descriptions[shot_idx].ff_vis_char_idxs],
                    character_portraits_registry=character_portraits_registry,
                )
            if shot_idx in priority_shot_idxs:
                priority_tasks.append(first_frame_task)
            else:
                normal_tasks.append(first_frame_task)


            if shot_descriptions[shot_idx].variation_type in ["medium", "large"]:
                last_frame_task = self.generate_frame_for_single_shot(
                    shot_idx=shot_idx, 
                    frame_type="last_frame", 
                    first_shot_ff_path_and_text_pair=(first_shot_ff_path, shot_descriptions[first_shot_idx].ff_desc),
                    frame_desc=shot_descriptions[shot_idx].lf_desc,
                    visible_characters=[characters[idx] for idx in shot_descriptions[shot_idx].lf_vis_char_idxs],
                    character_portraits_registry=character_portraits_registry,
                )
                normal_tasks.append(last_frame_task)


        await asyncio.gather(*priority_tasks)
        await asyncio.gather(*normal_tasks)



    async def generate_video_for_single_shot(
        self,
        shot_description: ShotDescription,
        prev_shot_last_frame_path: Optional[str] = None,
    ) -> Optional[str]:
        video_path = os.path.join(self.working_dir, "shots", f"{shot_description.idx}", "video.mp4")
        if ensure_valid_cached_video(video_path, f"shot {shot_description.idx} video"):
            print(f"🚀 Skipped generating video for shot {shot_description.idx}, already exists.")
            end_reference = self._resolve_shot_end_reference(shot_description.idx, video_path)
            return end_reference or prev_shot_last_frame_path

        if "first_frame" in self.frame_events[shot_description.idx]:
            await self.frame_events[shot_description.idx]["first_frame"].wait()
        if shot_description.variation_type in ["medium", "large"] and not getattr(self, "_fast_single_clip", False):
            await self.frame_events[shot_description.idx]["last_frame"].wait()

        frame_paths = self._build_video_reference_paths(
            shot_description,
            prev_shot_last_frame_path,
        )

        shot_duration = getattr(self, "_shot_duration", 5)
        print(
            f"🎬 Starting video generation for shot {shot_description.idx} "
            f"({shot_duration}s, refs={len(frame_paths)})..."
        )
        video_prompt = build_seedance_video_prompt(
            shot_description.motion_desc,
            shot_description.audio_desc,
            duration_seconds=shot_duration,
        )
        video_prompt = f"{video_prompt}\n\nVisual style: {self._video_style_prompt}"
        if self._scene_anchor_path and os.path.exists(self._scene_anchor_path):
            video_prompt += (
                "\nKeep the same fixed scene background, room layout, props, and lighting "
                "throughout the clip."
            )
        video_output = await self.video_generator.generate_single_video(
            prompt=video_prompt,
            reference_image_paths=frame_paths,
            duration=shot_duration,
            aspect_ratio=self._aspect_ratio,
            style=self._style,
            resolution=self._resolution,
            moderation_rewrite_callback=lambda rejected_paths, error: self._rewrite_rejected_video_reference(
                shot_description,
                rejected_paths,
                error,
            ),
        )
        video_output.save(video_path)
        api_last_frame_url = getattr(video_output, "last_frame_url", None)
        end_reference = self._resolve_shot_end_reference(
            shot_description.idx,
            video_path,
            api_last_frame_url=api_last_frame_url,
        )
        print(f"☑️ Generated video for shot {shot_description.idx}, saved to {video_path}.")
        cb = getattr(self, "_progress_callback", None)
        if cb:
            await cb({
                "type": "artifact", "stage": "videos", "file_type": "video",
                "file_path": os.path.join("shots", f"{shot_description.idx}", "video.mp4"),
                "shot_idx": shot_description.idx,
            })
        return end_reference or prev_shot_last_frame_path

    async def generate_frame_for_single_shot(
        self,
        shot_idx: int,
        frame_type: Literal["first_frame", "last_frame"],
        first_shot_ff_path_and_text_pair: Tuple[str, str],
        frame_desc: str,
        visible_characters: List[CharacterInScene],
        character_portraits_registry: Dict[str, Dict[str, Dict[str, str]]],
        prev_shot_end_reference: Optional[Tuple[str, str]] = None,
    ) -> ImageOutput:

        if frame_type == "last_frame":
            frame_desc = _safe_last_frame_description(frame_desc)

        frame_image_path = os.path.join(self.working_dir, "shots", f"{shot_idx}", f"{frame_type}.png")

        if os.path.exists(frame_image_path):
            print(f"🚀 Skipped generating {frame_type} for shot {shot_idx}, already exists.")

        else:
            print(f"🖼️ Starting {frame_type} generation for shot {shot_idx}...")
            available_image_path_and_text_pairs = []
            if self._scene_anchor_path and os.path.exists(self._scene_anchor_path):
                available_image_path_and_text_pairs.append(self._scene_anchor_pair())
            if prev_shot_end_reference and frame_type == "first_frame":
                available_image_path_and_text_pairs.append(prev_shot_end_reference)
            for visible_character in visible_characters:
                identifier_in_scene = visible_character.identifier_in_scene
                registry_item = character_portraits_registry[identifier_in_scene]
                for view, item in registry_item.items():
                    available_image_path_and_text_pairs.append((item["path"], item["description"]))

            # Same-camera anchor: only when the first-shot first_frame file already exists.
            # Skip while generating that file itself (serial keyframe shot 0 would FileNotFoundError).
            first_shot_ff_path, first_shot_ff_text = first_shot_ff_path_and_text_pair
            if os.path.exists(first_shot_ff_path):
                available_image_path_and_text_pairs.append((first_shot_ff_path, first_shot_ff_text))

            selector_output_path = os.path.join(self.working_dir, "shots", f"{shot_idx}", f"{frame_type}_selector_output.json")
            if os.path.exists(selector_output_path):
                with open(selector_output_path, 'r', encoding='utf-8') as f:
                    selector_output = json.load(f)
                print(f"🚀 Loaded existing reference image selection and prompt for {frame_type} frame of shot {shot_idx} from {selector_output_path}.")
            else:
                print(f"🔍 Selecting reference images and generating prompt for {frame_type} frame of shot {shot_idx}...")
                selector_output = await self.reference_image_selector.select_reference_images_and_generate_prompt(
                    available_image_path_and_text_pairs=available_image_path_and_text_pairs,
                    frame_description=frame_desc
                )
                with open(selector_output_path, 'w', encoding='utf-8') as f:
                    json.dump(selector_output, f, ensure_ascii=False, indent=4)
                print(f"☑️ Selected reference images and generated prompt for {frame_type} frame of shot {shot_idx}, saved to {selector_output_path}.")

            reference_image_path_and_text_pairs, prompt = selector_output["reference_image_path_and_text_pairs"], selector_output["text_prompt"]
            prefix_prompt = ""
            for i, (image_path, text) in enumerate(reference_image_path_and_text_pairs):
                prefix_prompt += f"Image {i}: {text}\n"
            prompt = f"{prefix_prompt}\n{prompt}\nStyle: {self._style_prompt}"
            reference_image_paths = [item[0] for item in reference_image_path_and_text_pairs]

            await self._save_generated_frame(
                frame_image_path=frame_image_path,
                prompt=prompt,
                reference_image_paths=reference_image_paths,
                reference_image_path_and_text_pairs=reference_image_path_and_text_pairs,
                target_description=frame_desc,
            )
            print(f"☑️ Generated {frame_type} frame for shot {shot_idx}, saved to {frame_image_path}.")
            cb = getattr(self, "_progress_callback", None)
            if cb:
                await cb({
                    "type": "artifact", "stage": "frames", "file_type": "image",
                    "file_path": os.path.join("shots", f"{shot_idx}", f"{frame_type}.png"),
                    "shot_idx": shot_idx, "frame_type": frame_type,
                })


        self.frame_events[shot_idx][frame_type].set()
        return frame_image_path


    async def construct_camera_tree(
        self,
        shot_descriptions: List[ShotDescription],
    ):
        camera_tree_path = os.path.join(self.working_dir, "camera_tree.json")

        if os.path.exists(camera_tree_path):
            with open(camera_tree_path, "r", encoding="utf-8") as f:
                camera_tree = json.load(f)
            camera_tree = [Camera.model_validate(camera) for camera in camera_tree]
            print(f"🚀 Loaded {len(camera_tree)} cameras from existing file.")
            return camera_tree

        cameras_by_idx: Dict[int, Camera] = {}
        for shot_description in shot_descriptions:
            cam_idx = shot_description.cam_idx
            if cam_idx not in cameras_by_idx:
                cameras_by_idx[cam_idx] = Camera(idx=cam_idx, active_shot_idxs=[shot_description.idx])
            else:
                cameras_by_idx[cam_idx].active_shot_idxs.append(shot_description.idx)
        cameras = list(cameras_by_idx.values())

        if getattr(self, "_fast_single_clip", False) and len(shot_descriptions) == 1:
            shot = shot_descriptions[0]
            camera_tree = [Camera(idx=shot.cam_idx, active_shot_idxs=[shot.idx])]
            with open(camera_tree_path, "w", encoding="utf-8") as f:
                json.dump([camera.model_dump() for camera in camera_tree], f, ensure_ascii=False, indent=4)
            print("⚡ Fast single-clip mode: using trivial single-camera tree (no LLM).")
            return camera_tree

        camera_tree = await self.camera_image_generator.construct_camera_tree(cameras=cameras, shot_descs=shot_descriptions)
        with open(camera_tree_path, "w", encoding="utf-8") as f:
            json.dump([camera.model_dump() for camera in camera_tree], f, ensure_ascii=False, indent=4)
        print(f"✅ Constructed camera tree and saved to {camera_tree_path}.")
        return camera_tree




    async def extract_characters(
        self,
        script: str,
    ):
        save_path = os.path.join(self.working_dir, "characters.json")

        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                characters = json.load(f)
            characters = [CharacterInScene.model_validate(character) for character in characters]
            print(f"🚀 Loaded {len(characters)} characters from existing file.")
        else:
            characters = await self.character_extractor.extract_characters(script)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump([character.model_dump() for character in characters], f, ensure_ascii=False, indent=4)
            print(f"✅ Extracted {len(characters)} characters from script and saved to {save_path}.")

        for character in characters:
            self.character_portrait_events[character.idx] = asyncio.Event()

        return characters


    async def generate_character_portraits(
        self,
        characters: List[CharacterInScene],
        character_portraits_registry: Optional[Dict[str, Dict[str, Dict[str, str]]]],
        style: str,
    ):
        character_portraits_registry_path = os.path.join(self.working_dir, "character_portraits_registry.json")
        if character_portraits_registry is None:
            if os.path.exists(character_portraits_registry_path):
                with open(character_portraits_registry_path, 'r', encoding='utf-8') as f:
                    character_portraits_registry = json.load(f)
            else:
                character_portraits_registry = {}


        tasks = [
            self.generate_portraits_for_single_character(character, style)
            for character in characters
            if character.identifier_in_scene not in character_portraits_registry
        ]
        if tasks:
            for future in asyncio.as_completed(tasks):
                character_portraits_registry.update(await future)
                with open(character_portraits_registry_path, 'w', encoding='utf-8') as f:
                    json.dump(character_portraits_registry, f, ensure_ascii=False, indent=4)

            print(f"✅ Completed character portrait generation for {len(characters)} characters.")
        else:
            print("🚀 All characters already have portraits, skipping portrait generation.")
        if not character_portraits_registry:
            print("ℹ️ No visible characters to generate portraits for.")
        return character_portraits_registry

    async def _emit_character_portrait_artifacts(
        self,
        character_portraits_registry: Dict[str, Dict[str, Dict[str, str]]],
        cb,
    ) -> None:
        for character_name, views in character_portraits_registry.items():
            for view_name, view_data in views.items():
                path = view_data.get("path") if isinstance(view_data, dict) else None
                if not path or not os.path.exists(path):
                    continue
                await cb({
                    "type": "artifact",
                    "stage": "character_portraits",
                    "file_type": "image",
                    "file_path": os.path.relpath(path, self.working_dir).replace(os.sep, "/"),
                    "character_name": character_name,
                    "view": view_name,
                })


    async def generate_portraits_for_single_character(
        self,
        character: CharacterInScene,
        style: str,
    ):
        character_dir = os.path.join(self.working_dir, "character_portraits", f"{character.idx}_{character.identifier_in_scene}")
        os.makedirs(character_dir, exist_ok=True)

        front_portrait_path = os.path.join(character_dir, "front.png")
        side_portrait_path = os.path.join(character_dir, "side.png")
        back_portrait_path = os.path.join(character_dir, "back.png")

        all_exist = all(os.path.exists(p) for p in [front_portrait_path, side_portrait_path, back_portrait_path])
        portrait_kwargs = self._portrait_image_gen_kwargs
        if all_exist:
            pass
        elif self.USE_TURNAROUND_SHEET:
            try:
                turnaround_output = await self.character_portraits_generator.generate_turnaround_sheet(
                    character,
                    style,
                    image_gen_kwargs=portrait_kwargs(turnaround=True),
                )
                sheet_pil = image_output_to_pil(turnaround_output)
                paths = crop_turnaround_views(sheet_pil, character_dir)
                front_portrait_path = paths.get("front", front_portrait_path)
                side_portrait_path = paths.get("side", side_portrait_path)
                back_portrait_path = paths.get("back", back_portrait_path)
            except Exception as e:
                logging.warning(
                    f"Turnaround sheet generation failed for {character.identifier_in_scene}: {e}. "
                    f"Falling back to 3 separate calls."
                )
                await self._generate_portraits_individual(
                    character, style, character_dir,
                    front_portrait_path, side_portrait_path, back_portrait_path
                )
        else:
            await self._generate_portraits_individual(
                character, style, character_dir,
                front_portrait_path, side_portrait_path, back_portrait_path
            )

        self.character_portrait_events[character.idx].set()

        print(f"☑️ Completed character portrait generation for {character.identifier_in_scene}.")

        # Emit portrait artifact events
        cb = getattr(self, "_progress_callback", None)
        if cb:
            for view_name, path in [("front", front_portrait_path), ("side", side_portrait_path), ("back", back_portrait_path)]:
                await cb({
                    "type": "artifact", "stage": "character_portraits", "file_type": "image",
                    "file_path": os.path.relpath(path, self.working_dir),
                    "character_name": character.identifier_in_scene, "view": view_name,
                })

        features_summary = f"{character.identifier_in_scene}: {character.static_features} {character.dynamic_features}"
        return {
            character.identifier_in_scene: {
                "front": {
                    "path": front_portrait_path,
                    "description": f"A front view portrait of {character.identifier_in_scene}. {features_summary}",
                },
                "side": {
                    "path": side_portrait_path,
                    "description": f"A side view portrait of {character.identifier_in_scene}. {features_summary}",
                },
                "back": {
                    "path": back_portrait_path,
                    "description": f"A back view portrait of {character.identifier_in_scene}. {features_summary}",
                },
            }
        }

    async def _generate_portraits_individual(
        self,
        character: CharacterInScene,
        style: str,
        character_dir: str,
        front_path: str,
        side_path: str,
        back_path: str,
    ):
        """Fallback: generate 3 separate portrait images (front, side, back)."""
        portrait_kwargs = self._portrait_image_gen_kwargs
        if not os.path.exists(front_path):
            front_output = await self.character_portraits_generator.generate_front_portrait(
                character, style, image_gen_kwargs=portrait_kwargs(turnaround=False),
            )
            front_output.save(front_path)
        if not os.path.exists(side_path):
            side_output = await self.character_portraits_generator.generate_side_portrait(
                character, front_path, style, image_gen_kwargs=portrait_kwargs(turnaround=False),
            )
            side_output.save(side_path)
        if not os.path.exists(back_path):
            back_output = await self.character_portraits_generator.generate_back_portrait(
                character, front_path, style, image_gen_kwargs=portrait_kwargs(turnaround=False),
            )
            back_output.save(back_path)



    async def design_storyboard(
        self,
        script: str,
        characters: List[CharacterInScene],
        user_requirement: str,
        episode_duration: int = 0,
    ):
        storyboard_path = os.path.join(self.working_dir, "storyboard.json")
        max_shots = resolve_max_shots(user_requirement, episode_duration)
        storyboard_requirement = user_requirement
        if max_shots == 1:
            storyboard_requirement = (
                f"{user_requirement}\n\n"
                "CRITICAL: The storyboard must contain EXACTLY ONE shot (idx=0, is_last=true). "
                "Do not split into multiple shots."
            )
        elif max_shots is not None:
            storyboard_requirement = (
                f"{user_requirement}\n\n"
                f"CRITICAL: The storyboard must contain AT MOST {max_shots} shots."
            )

        if os.path.exists(storyboard_path):
            with open(storyboard_path, 'r', encoding='utf-8') as f:
                storyboard = json.load(f)
            storyboard = [ShotBriefDescription.model_validate(shot) for shot in storyboard]
            print(f"🚀 Loaded {len(storyboard)} shot brief descriptions from existing file.")
        else:
            print(f"🔍 Designing storyboard...")
            storyboard = await self.storyboard_artist.design_storyboard(
                script=script,
                characters=characters,
                user_requirement=storyboard_requirement,
                retry_timeout=150,
            )
            with open(storyboard_path, 'w', encoding='utf-8') as f:
                json.dump([shot.model_dump() for shot in storyboard], f, ensure_ascii=False, indent=4)
            print(f"✅ Designed storyboard and saved to {storyboard_path}.")

        if max_shots is not None and len(storyboard) > max_shots:
            storyboard = storyboard[:max_shots]
            if len(storyboard) == 1:
                storyboard[0].is_last = True
            print(f"✂️ Limited storyboard to {max_shots} shot(s) for target duration.")
            with open(storyboard_path, 'w', encoding='utf-8') as f:
                json.dump([shot.model_dump() for shot in storyboard], f, ensure_ascii=False, indent=4)
            _invalidate_final_video_cache(self.working_dir)

        allowed_shot_idxs = {shot.idx for shot in storyboard}
        if _cleanup_stale_shot_dirs(self.working_dir, allowed_shot_idxs):
            _invalidate_final_video_cache(self.working_dir)

        for shot_brief_description in storyboard:
            self.shot_desc_events[shot_brief_description.idx] = asyncio.Event()

        return storyboard



    async def decompose_visual_descriptions(
        self,
        shot_brief_descriptions: List[ShotBriefDescription],
        characters: List[CharacterInScene],
    ):
        tasks = [
            self.decompose_visual_description_for_single_shot_brief_description(shot_brief_description, characters)
            for shot_brief_description in shot_brief_descriptions
        ]

        shot_descriptions = await asyncio.gather(*tasks)
        return shot_descriptions


    async def decompose_visual_description_for_single_shot_brief_description(
        self,
        shot_brief_description: ShotBriefDescription,
        characters: List[CharacterInScene],
    ):
        shot_description_path = os.path.join(self.working_dir, "shots", f"{shot_brief_description.idx}", "shot_description.json")
        os.makedirs(os.path.dirname(shot_description_path), exist_ok=True)

        if os.path.exists(shot_description_path):
            with open(shot_description_path, 'r', encoding='utf-8') as f:
                shot_description = ShotDescription.model_validate(json.load(f))
            print(f"🚀 Loaded shot {shot_brief_description.idx} description from existing file.")
        else:
            shot_description = await self.storyboard_artist.decompose_visual_description(
                shot_brief_desc=shot_brief_description,
                characters=characters,
                retry_timeout=120,
            )
            with open(shot_description_path, 'w', encoding='utf-8') as f:
                json.dump(shot_description.model_dump(), f, ensure_ascii=False, indent=4)
            print(f"✅ Decomposed visual description for shot {shot_brief_description.idx} and saved to {shot_description_path}.")

        self.shot_desc_events[shot_brief_description.idx].set()

        if shot_description.variation_type in ["medium", "large"]:
            self.frame_events[shot_brief_description.idx] = {
                "first_frame": asyncio.Event(),
                "last_frame": asyncio.Event(),
            }
        else:
            self.frame_events[shot_brief_description.idx] = {
                "first_frame": asyncio.Event(),
            }

        return shot_description