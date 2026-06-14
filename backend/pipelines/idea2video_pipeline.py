import os
import logging
import time
from agents import Screenwriter, CharacterExtractor, CharacterPortraitsGenerator
from pipelines.script2video_pipeline import Script2VideoPipeline
from interfaces import CharacterInScene
from typing import List, Dict, Optional, Callable, Awaitable
import asyncio
import json

import yaml
from langchain.chat_models import init_chat_model
from tools.render_backend import RenderBackend
from utils.provider_presets import resolve_chat_model_config
from utils.image import image_output_to_pil, crop_turnaround_views
from utils.pipeline_media import aspect_ratio_llm_hint
from agents.best_image_selector import BestImageSelector


async def _noop_progress(_event):
    pass


ORIGINAL_CONTENT_REQUIREMENT = (
    "原创虚构角色与场景，避免模仿知名影视或宗教地标。"
)


def build_effective_user_requirement(
    user_requirement: str,
    episode_count: int = 0,
    episode_duration: int = 0,
    aspect_ratio: str = "",
) -> str:
    """Merge UI episode settings into prompts the LLM and storyboard must follow."""
    parts = []
    if user_requirement and user_requirement.strip():
        parts.append(user_requirement.strip())
    if aspect_ratio and f"Aspect ratio: {aspect_ratio}" not in " ".join(parts):
        parts.append(f"Aspect ratio: {aspect_ratio}")
        parts.append(aspect_ratio_llm_hint(aspect_ratio))
    if episode_count == 1:
        parts.append(
            "Generate exactly ONE episode as a single short video. "
            "The script must contain exactly ONE scene (single time and location). "
            "Do not split into multiple acts or scenes."
        )
    elif episode_count > 1:
        parts.append(
            f"Generate exactly {episode_count} episodes; "
            f"each episode should map to one scene in the script."
        )
    if episode_duration > 0:
        max_shots = max(1, min(3, episode_duration // 5))
        parts.append(
            f"Target episode duration: approximately {episode_duration} seconds. "
            f"Use at most {max_shots} shots in the storyboard."
        )
        parts.append(
            "Use exactly ONE camera position for the entire scene when possible. "
            "Keep the same background, props, lighting, and room layout across all shots. "
            "Prefer 2-3 shots total with minimal camera movement."
        )
        parts.append(
            "Short drama pacing: hook the audience in the first 3 seconds, "
            "build one clear conflict, use speakable dialogue, "
            "and align SHOT blocks to roughly 5 seconds each."
        )
    if ORIGINAL_CONTENT_REQUIREMENT not in " ".join(parts):
        parts.append(ORIGINAL_CONTENT_REQUIREMENT)
    return " ".join(parts)


def limit_scene_scripts(scene_scripts: List[str], episode_count: int) -> List[str]:
    """Enforce episode count even when cached script.json has more scenes."""
    if episode_count == 1:
        return scene_scripts[:1]
    if episode_count > 1:
        return scene_scripts[:episode_count]
    return scene_scripts


class Idea2VideoPipeline:

    # Use turnaround sheet (single image with 3 views) for better character consistency.
    # Set to False to fall back to the old 3-separate-call method.
    USE_TURNAROUND_SHEET = True
    def __init__(
        self,
        chat_model: str,
        image_generator: str,
        video_generator: str,
        working_dir: str,
        multimodal_chat_model=None,
        best_image_selector: Optional[BestImageSelector] = None,
    ):
        self.chat_model = chat_model
        self.image_generator = image_generator
        self.video_generator = video_generator
        self.working_dir = working_dir
        self.multimodal_chat_model = multimodal_chat_model
        self.best_image_selector = best_image_selector
        os.makedirs(self.working_dir, exist_ok=True)

        self.screenwriter = Screenwriter(chat_model=self.chat_model)
        self.character_extractor = CharacterExtractor(
            chat_model=self.chat_model)
        self.character_portraits_generator = CharacterPortraitsGenerator(
            image_generator=self.image_generator)

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

    async def extract_characters(
        self,
        story: str,
    ):
        save_path = os.path.join(self.working_dir, "characters.json")

        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                characters = json.load(f)
            characters = [CharacterInScene.model_validate(
                character) for character in characters]
            print(f"Loaded {len(characters)} characters from existing file.")
        else:
            characters = await self.character_extractor.extract_characters(story)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump([character.model_dump()
                          for character in characters], f, ensure_ascii=False, indent=4)
            print(
                f"Extracted {len(characters)} characters from story and saved to {save_path}.")

        return characters

    async def generate_character_portraits(
        self,
        characters: List[CharacterInScene],
        character_portraits_registry: Optional[Dict[str, Dict[str, Dict[str, str]]]],
        style: str,
    ):
        character_portraits_registry_path = os.path.join(
            self.working_dir, "character_portraits_registry.json")
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
                    json.dump(character_portraits_registry,
                              f, ensure_ascii=False, indent=4)

            print(
                f"Completed character portrait generation for {len(characters)} characters.")
        else:
            print(
                "All characters already have portraits, skipping portrait generation.")

        return character_portraits_registry

    async def develop_story(
        self,
        idea: str,
        user_requirement: str,
    ):
        save_path = os.path.join(self.working_dir, "story.txt")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                story = f.read()
            print(f"Loaded story from existing file.")
        else:
            print("🧠 Developing story...")
            story = await self.screenwriter.develop_story(idea=idea, user_requirement=user_requirement)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(story)
            print(f"Developed story and saved to {save_path}.")

        return story

    async def write_script_based_on_story(
        self,
        story: str,
        user_requirement: str,
        aspect_ratio: str = "",
    ):
        save_path = os.path.join(self.working_dir, "script.json")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                script = json.load(f)
            print(f"Loaded script from existing file.")
        else:
            print("🧠 Writing script based on story...")
            script = await self.screenwriter.write_script_based_on_story(
                story=story, user_requirement=user_requirement
            )
            polished_scripts = []
            for idx, scene_script in enumerate(script):
                print(f"Polishing scene script {idx + 1}/{len(script)}...")
                polished_scripts.append(
                    await self.screenwriter.polish_scene_script(
                        scene_script,
                        user_requirement=user_requirement,
                        aspect_ratio=aspect_ratio,
                    )
                )
            script = polished_scripts
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=4)
            print(f"Written script based on story and saved to {save_path}.")
        return script

    async def generate_portraits_for_single_character(
        self,
        character: CharacterInScene,
        style: str,
    ):
        character_dir = os.path.join(
            self.working_dir, "character_portraits", f"{character.idx}_{character.identifier_in_scene}")
        os.makedirs(character_dir, exist_ok=True)

        front_portrait_path = os.path.join(character_dir, "front.png")
        side_portrait_path = os.path.join(character_dir, "side.png")
        back_portrait_path = os.path.join(character_dir, "back.png")

        all_exist = all(os.path.exists(p) for p in [front_portrait_path, side_portrait_path, back_portrait_path])
        if all_exist:
            pass
        elif self.USE_TURNAROUND_SHEET:
            try:
                turnaround_output = await self.character_portraits_generator.generate_turnaround_sheet(character, style)
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

        print(
            f"Completed character portrait generation for {character.identifier_in_scene}.")

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
        if not os.path.exists(front_path):
            front_output = await self.character_portraits_generator.generate_front_portrait(character, style)
            front_output.save(front_path)
        if not os.path.exists(side_path):
            side_output = await self.character_portraits_generator.generate_side_portrait(character, front_path, style)
            side_output.save(side_path)
        if not os.path.exists(back_path):
            back_output = await self.character_portraits_generator.generate_back_portrait(character, front_path, style)
            back_output.save(back_path)

    async def __call__(
        self,
        idea: str,
        user_requirement: str,
        style: str,
        episode_count: int = 0,
        episode_duration: int = 0,
        aspect_ratio: str = "",
        progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        cb = progress_callback or _noop_progress
        self._progress_callback = cb
        from utils.pipeline_media import resolve_aspect_ratio

        self._aspect_ratio = resolve_aspect_ratio(user_requirement, explicit=aspect_ratio or None)
        effective_requirement = build_effective_user_requirement(
            user_requirement, episode_count, episode_duration, self._aspect_ratio
        )

        # Stage: Story
        await cb({"type": "stage_start", "stage": "story", "message": "Developing story from idea..."})
        t0 = time.time()
        story = await self.develop_story(idea=idea, user_requirement=effective_requirement)
        story_path = os.path.join(self.working_dir, "story.txt")
        await cb({
            "type": "artifact", "stage": "story", "file_type": "text",
            "file_path": "story.txt", "content_preview": story[:500],
        })
        await cb({"type": "stage_end", "stage": "story", "duration_ms": int((time.time() - t0) * 1000)})

        # Stage: Characters
        await cb({"type": "stage_start", "stage": "characters", "message": "Extracting characters from story..."})
        t0 = time.time()
        characters = await self.extract_characters(story=story)
        await cb({
            "type": "artifact", "stage": "characters", "file_type": "json",
            "file_path": "characters.json",
            "character_count": len(characters),
            "content_preview": json.dumps([c.model_dump() for c in characters], ensure_ascii=False, indent=2)[:500],
        })
        await cb({"type": "stage_end", "stage": "characters", "duration_ms": int((time.time() - t0) * 1000)})

        # Stage: Character Portraits
        await cb({"type": "stage_start", "stage": "character_portraits", "message": f"Generating portraits for {len(characters)} characters..."})
        t0 = time.time()
        character_portraits_registry = await self.generate_character_portraits(
            characters=characters,
            character_portraits_registry=None,
            style=style,
        )
        await cb({"type": "stage_end", "stage": "character_portraits", "duration_ms": int((time.time() - t0) * 1000)})

        # Stage: Script
        await cb({"type": "stage_start", "stage": "script", "message": "Writing script based on story..."})
        t0 = time.time()
        scene_scripts = await self.write_script_based_on_story(
            story=story,
            user_requirement=effective_requirement,
            aspect_ratio=self._aspect_ratio,
        )
        raw_scene_count = len(scene_scripts)
        scene_scripts = limit_scene_scripts(scene_scripts, episode_count)
        if episode_count > 0 and raw_scene_count > len(scene_scripts):
            print(
                f"✂️ Using {len(scene_scripts)} of {raw_scene_count} script scene(s) "
                f"for {episode_count} requested episode(s)."
            )
        await cb({
            "type": "artifact", "stage": "script", "file_type": "json",
            "file_path": "script.json",
            "content_preview": json.dumps(scene_scripts, ensure_ascii=False, indent=2)[:500],
        })
        await cb({"type": "stage_end", "stage": "script", "duration_ms": int((time.time() - t0) * 1000), "scene_count": len(scene_scripts)})

        # Stage: Per-scene processing
        total_scenes = len(scene_scripts)
        all_video_paths = []

        for idx, scene_script in enumerate(scene_scripts):
            scene_stage = f"scene_{idx}"
            await cb({"type": "stage_start", "stage": scene_stage, "message": f"Processing scene {idx + 1}/{total_scenes}...", "scene_index": idx, "total_scenes": total_scenes})
            print(f"[Scene {idx + 1}/{total_scenes}] Processing scene...")
            scene_working_dir = os.path.join(self.working_dir, f"scene_{idx}")
            os.makedirs(scene_working_dir, exist_ok=True)
            script2video_pipeline = Script2VideoPipeline(
                chat_model=self.chat_model,
                image_generator=self.image_generator,
                video_generator=self.video_generator,
                working_dir=scene_working_dir,
                multimodal_chat_model=self.multimodal_chat_model,
                best_image_selector=self.best_image_selector,
            )
            # Wrap callback to scope artifact paths under this scene directory
            rel_scene_dir = os.path.relpath(scene_working_dir, self.working_dir)
            async def scoped_cb(event):
                if event.get("type") == "artifact" and "file_path" in event:
                    event = dict(event)
                    event["file_path"] = os.path.join(
                        rel_scene_dir,
                        event["file_path"],
                    ).replace(os.sep, "/")
                await cb(event)

            final_video_path = await script2video_pipeline(
                script=scene_script,
                user_requirement=effective_requirement,
                style=style,
                characters=characters,
                character_portraits_registry=character_portraits_registry,
                aspect_ratio=self._aspect_ratio,
                progress_callback=scoped_cb,
            )
            await cb({
                "type": "artifact", "stage": scene_stage, "file_type": "video",
                "file_path": os.path.relpath(final_video_path, self.working_dir).replace(os.sep, "/"),
            })
            all_video_paths.append(final_video_path)
            await cb({"type": "stage_end", "stage": scene_stage, "message": f"Scene {idx + 1}/{total_scenes} completed"})

        # Stage: Concatenate
        final_video_path = os.path.join(self.working_dir, "final_video.mp4")
        from utils.video import ensure_valid_cached_video
        if ensure_valid_cached_video(final_video_path, "episode final video"):
            print(f"Skipped concatenating videos, already exists.")
            await cb({"type": "stage_end", "stage": "concatenate", "message": "Final video already exists"})
        else:
            await cb({"type": "stage_start", "stage": "concatenate", "message": "Concatenating all scene videos..."})
            t0 = time.time()
            print(f"Starting concatenating videos...")
            from utils.video import concat_videos
            from utils.pipeline_media import concat_dimensions_for_aspect
            width, height = concat_dimensions_for_aspect(self._aspect_ratio)
            concat_videos(
                all_video_paths,
                final_video_path,
                target_width=width,
                target_height=height,
                crossfade_seconds=0.12,
            )
            print(f"Concatenated videos, saved to {final_video_path}.")
            await cb({"type": "stage_end", "stage": "concatenate", "duration_ms": int((time.time() - t0) * 1000)})

        await cb({
            "type": "artifact", "stage": "concatenate", "file_type": "video",
            "file_path": "final_video.mp4",
        })

        self._progress_callback = None
        return final_video_path
