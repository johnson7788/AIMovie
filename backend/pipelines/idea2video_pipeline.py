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


class Idea2VideoPipeline:
    def __init__(
        self,
        chat_model: str,
        image_generator: str,
        video_generator: str,
        working_dir: str,
    ):
        self.chat_model = chat_model
        self.image_generator = image_generator
        self.video_generator = video_generator
        self.working_dir = working_dir
        os.makedirs(self.working_dir, exist_ok=True)

        self.screenwriter = Screenwriter(chat_model=self.chat_model)
        self.character_extractor = CharacterExtractor(
            chat_model=self.chat_model)
        self.character_portraits_generator = CharacterPortraitsGenerator(
            image_generator=self.image_generator)

    @classmethod
    def init_from_config(cls, config_path: str):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        chat_model_args = resolve_chat_model_config(config["chat_model"]["init_args"])
        chat_model = init_chat_model(**chat_model_args)
        backend = RenderBackend.from_config(config)

        return cls(
            chat_model=chat_model,
            image_generator=backend.image_generator,
            video_generator=backend.video_generator,
            working_dir=config["working_dir"],
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
            print(f"🚀 Loaded {len(characters)} characters from existing file.")
        else:
            characters = await self.character_extractor.extract_characters(story)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump([character.model_dump()
                          for character in characters], f, ensure_ascii=False, indent=4)
            print(
                f"✅ Extracted {len(characters)} characters from story and saved to {save_path}.")

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
                f"✅ Completed character portrait generation for {len(characters)} characters.")
        else:
            print(
                "🚀 All characters already have portraits, skipping portrait generation.")

        return character_portraits_registry

    async def develop_story(
        self,
        idea: str,
        user_requirement: str,
        episode_count: int = 0,
    ):
        save_path = os.path.join(self.working_dir, "story.txt")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                story = f.read()
            print(f"🚀 Loaded story from existing file.")
        else:
            print("🧠 Developing story...")
            effective_requirement = user_requirement
            if episode_count > 0:
                effective_requirement = f"{user_requirement}\nEpisodes: {episode_count}"
            story = await self.screenwriter.develop_story(idea=idea, user_requirement=effective_requirement)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(story)
            print(f"✅ Developed story and saved to {save_path}.")

        return story

    async def write_script_based_on_story(
        self,
        story: str,
        user_requirement: str,
    ):
        save_path = os.path.join(self.working_dir, "script.json")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                script = json.load(f)
            print(f"🚀 Loaded script from existing file.")
        else:
            print("🧠 Writing script based on story...")
            script = await self.screenwriter.write_script_based_on_story(story=story, user_requirement=user_requirement)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=4)
            print(f"✅ Written script based on story and saved to {save_path}.")
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
        if os.path.exists(front_portrait_path):
            pass
        else:
            front_portrait_output = await self.character_portraits_generator.generate_front_portrait(character, style)
            front_portrait_output.save(front_portrait_path)

        side_portrait_path = os.path.join(character_dir, "side.png")
        if os.path.exists(side_portrait_path):
            pass
        else:
            side_portrait_output = await self.character_portraits_generator.generate_side_portrait(character, front_portrait_path, style)
            side_portrait_output.save(side_portrait_path)

        back_portrait_path = os.path.join(character_dir, "back.png")
        if os.path.exists(back_portrait_path):
            pass
        else:
            back_portrait_output = await self.character_portraits_generator.generate_back_portrait(character, front_portrait_path, style)
            back_portrait_output.save(back_portrait_path)

        print(
            f"☑️ Completed character portrait generation for {character.identifier_in_scene}.")

        # Emit portrait artifact events
        cb = getattr(self, "_progress_callback", None)
        if cb:
            for view_name, path in [("front", front_portrait_path), ("side", side_portrait_path), ("back", back_portrait_path)]:
                await cb({
                    "type": "artifact", "stage": "character_portraits", "file_type": "image",
                    "file_path": os.path.relpath(path, self.working_dir),
                    "character_name": character.identifier_in_scene, "view": view_name,
                })

        return {
            character.identifier_in_scene: {
                "front": {
                    "path": front_portrait_path,
                    "description": f"A front view portrait of {character.identifier_in_scene}.",
                },
                "side": {
                    "path": side_portrait_path,
                    "description": f"A side view portrait of {character.identifier_in_scene}.",
                },
                "back": {
                    "path": back_portrait_path,
                    "description": f"A back view portrait of {character.identifier_in_scene}.",
                },
            }
        }

    async def __call__(
        self,
        idea: str,
        user_requirement: str,
        style: str,
        episode_count: int = 0,
        progress_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        cb = progress_callback or (lambda e: None)
        self._progress_callback = cb

        # Stage: Story
        await cb({"type": "stage_start", "stage": "story", "message": "Developing story from idea..."})
        t0 = time.time()
        story = await self.develop_story(idea=idea, user_requirement=user_requirement, episode_count=episode_count)
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
        scene_scripts = await self.write_script_based_on_story(story=story, user_requirement=user_requirement)
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
            print(f"🎬 [Scene {idx + 1}/{total_scenes}] Processing scene...")
            scene_working_dir = os.path.join(self.working_dir, f"scene_{idx}")
            os.makedirs(scene_working_dir, exist_ok=True)
            script2video_pipeline = Script2VideoPipeline(
                chat_model=self.chat_model,
                image_generator=self.image_generator,
                video_generator=self.video_generator,
                working_dir=scene_working_dir,
            )
            # Wrap callback to scope artifact paths under this scene directory
            rel_scene_dir = os.path.relpath(scene_working_dir, self.working_dir)
            async def scoped_cb(event):
                if event.get("type") == "artifact" and "file_path" in event:
                    event = dict(event)
                    event["file_path"] = os.path.join(rel_scene_dir, event["file_path"])
                await cb(event)

            final_video_path = await script2video_pipeline(
                script=scene_script,
                user_requirement=user_requirement,
                style=style,
                characters=characters,
                character_portraits_registry=character_portraits_registry,
                progress_callback=scoped_cb,
            )
            await cb({
                "type": "artifact", "stage": scene_stage, "file_type": "video",
                "file_path": os.path.relpath(final_video_path, self.working_dir),
            })
            all_video_paths.append(final_video_path)
            await cb({"type": "stage_end", "stage": scene_stage, "message": f"Scene {idx + 1}/{total_scenes} completed"})

        # Stage: Concatenate
        final_video_path = os.path.join(self.working_dir, "final_video.mp4")
        if os.path.exists(final_video_path):
            print(f"🚀 Skipped concatenating videos, already exists.")
        else:
            await cb({"type": "stage_start", "stage": "concatenate", "message": "Concatenating all scene videos..."})
            t0 = time.time()
            print(f"🎬 Starting concatenating videos...")
            from utils.video import concat_videos
            concat_videos(all_video_paths, final_video_path)
            print(f"☑️ Concatenated videos, saved to {final_video_path}.")
            await cb({"type": "stage_end", "stage": "concatenate", "duration_ms": int((time.time() - t0) * 1000)})

        await cb({
            "type": "artifact", "stage": "concatenate", "file_type": "video",
            "file_path": "final_video.mp4",
        })

        self._progress_callback = None
        return final_video_path
