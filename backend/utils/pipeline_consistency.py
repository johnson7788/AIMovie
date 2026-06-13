"""Helpers for shot/scene continuity across the script2video pipeline."""

from __future__ import annotations

import os
import re
from typing import List, Sequence

from interfaces import ShotDescription

SAME_CAMERA_CROSSFADE_SECONDS = 0.0
DIFFERENT_CAMERA_CROSSFADE_SECONDS = 0.12


def build_crossfade_schedule(
    shot_descriptions: Sequence[ShotDescription],
    *,
    same_camera_seconds: float = SAME_CAMERA_CROSSFADE_SECONDS,
    different_camera_seconds: float = DIFFERENT_CAMERA_CROSSFADE_SECONDS,
) -> List[float]:
    """Per-join crossfade duration. Same camera → hard cut (0s)."""
    if len(shot_descriptions) <= 1:
        return []
    schedule: List[float] = []
    for index in range(len(shot_descriptions) - 1):
        left = shot_descriptions[index].cam_idx
        right = shot_descriptions[index + 1].cam_idx
        if left == right:
            schedule.append(same_camera_seconds)
        else:
            schedule.append(different_camera_seconds)
    return schedule


def scene_anchor_prompt(script: str, style_prompt: str) -> str:
    """Prompt for an empty establishing shot reused as the scene anchor."""
    excerpt = (script or "").strip()
    if len(excerpt) > 900:
        excerpt = excerpt[:900] + "…"
    return (
        "Empty establishing wide shot of the scene location. "
        "No people, no characters, no faces, no silhouettes. "
        "Show only the environment, furniture, props, walls, lighting, and atmosphere. "
        "This image is the fixed scene anchor — the background layout must stay identical "
        "across all later shots in this scene.\n\n"
        f"Script location context:\n{excerpt}\n\n"
        f"Style: {style_prompt}"
    )


def scene_anchor_reference_text() -> str:
    return (
        "Scene establishing anchor — empty environment reference. "
        "Keep this exact room layout, background, props, and lighting consistent in every shot."
    )


def infer_scene_location_hint(script: str) -> str:
    """Best-effort location snippet for logging / progress."""
    text = (script or "").strip()
    match = re.search(r"(INT\.|EXT\.|内景|外景|场景)[^\n]{0,80}", text, re.IGNORECASE)
    return match.group(0).strip() if match else "scene location"


def video_last_frame_path(shot_idx: int, working_dir: str) -> str:
    return os.path.join(working_dir, "shots", str(shot_idx), "video_last_frame.png")
