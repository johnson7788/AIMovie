"""Helpers for shot/scene continuity across the script2video pipeline."""

from __future__ import annotations

import os
import re
import logging
from typing import List, Optional, Sequence

from interfaces import ShotDescription

SAME_CAMERA_CROSSFADE_SECONDS = 0.08
DIFFERENT_CAMERA_CROSSFADE_SECONDS = 0.2


def build_crossfade_schedule(
    shot_descriptions: Sequence[ShotDescription],
    *,
    same_camera_seconds: float = SAME_CAMERA_CROSSFADE_SECONDS,
    different_camera_seconds: float = DIFFERENT_CAMERA_CROSSFADE_SECONDS,
) -> List[float]:
    """Per-join crossfade duration. Even same-camera joins get a tiny blend."""
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


def storyboard_frame_path(shot_idx: int, working_dir: str, frame_type: str) -> str:
    return os.path.join(working_dir, "shots", str(shot_idx), f"{frame_type}.png")


def prev_shot_end_reference_text(prev_shot_idx: int) -> str:
    return (
        f"Previous shot {prev_shot_idx} ending frame — continue from this exact scene layout, "
        "lighting, props, and character positions at the cut point."
    )


def should_use_serial_keyframe_pipeline(
    camera_tree: Sequence,
    user_requirement: str = "",
) -> bool:
    """Serial keyframe mode: one shot fully finishes before the next starts."""
    if len(camera_tree) == 1:
        return True
    text = (user_requirement or "").lower()
    if "one camera position" in text or "exactly one camera" in text:
        return True
    return _is_short_form_episode(user_requirement)


def _is_short_form_episode(user_requirement: str) -> bool:
    """Short clips benefit more from temporal continuity than parallel frame throughput."""
    text = user_requirement or ""
    duration_match = re.search(
        r"(?:Episode duration|Target episode duration: approximately)\s*:?\s*(\d+)\s*(?:s|seconds)?",
        text,
        re.IGNORECASE,
    )
    if duration_match and int(duration_match.group(1)) <= 30:
        return True
    max_shots_match = re.search(r"Use at most (\d+) shots", text, re.IGNORECASE)
    return bool(max_shots_match and int(max_shots_match.group(1)) <= 4)


def resolve_shot_end_reference(
    working_dir: str,
    shot_idx: int,
    video_path: str,
    extract_last_frame,
    *,
    api_last_frame_url: Optional[str] = None,
) -> Optional[str]:
    """Best end-of-shot image for handing off to the next shot."""
    from utils.image import download_image

    video_last = video_last_frame_path(shot_idx, working_dir)

    if api_last_frame_url:
        try:
            download_image(api_last_frame_url, video_last)
            logging.info(
                "Saved Seedance API last frame for shot %s -> %s",
                shot_idx,
                video_last,
            )
            return video_last
        except Exception as exc:
            logging.warning(
                "Seedance API last-frame download failed for shot %s: %s",
                shot_idx,
                exc,
            )

    try:
        extract_last_frame(video_path, video_last)
        logging.info(
            "Using extracted video last frame for shot %s continuity: %s",
            shot_idx,
            video_last,
        )
        return video_last
    except Exception as exc:
        logging.warning(
            "Video last-frame extraction failed for shot %s: %s",
            shot_idx,
            exc,
        )

    for frame_type, label in (("last_frame", "storyboard last_frame"),):
        candidate = storyboard_frame_path(shot_idx, working_dir, frame_type)
        if os.path.exists(candidate):
            logging.info(
                "Using %s fallback for shot %s continuity: %s",
                label,
                shot_idx,
                candidate,
            )
            return candidate

    first_frame = storyboard_frame_path(shot_idx, working_dir, "first_frame")
    if os.path.exists(first_frame):
        logging.warning(
            "Using storyboard first_frame as weak end-of-shot fallback for shot %s: %s",
            shot_idx,
            first_frame,
        )
        return first_frame
    return None
