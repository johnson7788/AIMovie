"""Aspect ratio and output dimensions shared across video pipelines."""

from __future__ import annotations

import math
import re
from typing import Optional, Tuple

# Must match frontend xl-aspect-ratio options
SUPPORTED_ASPECT_RATIOS = (
    "9:16",
    "16:9",
    "3:4",
    "4:3",
    "2:3",
    "3:2",
    "1:1",
)

DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_VIDEO_RESOLUTION = "480p"
DEFAULT_SHORT_SIDE = 720
# GPUGEEK / Volcengine Seedream minimum output area (e.g. 1920x1920 = 3686400 px)
SEEDREAM_MIN_PIXELS = 3_686_400
# Seedance 2.0 (GPUGEEK): one reference task can output up to 15s.
SEEDANCE_SINGLE_CLIP_MAX_SECONDS = 15
SEEDANCE_SUPPORTED_DURATIONS = (4, 5, 10, 15)


def _even(value: int) -> int:
    return max(2, value - (value % 2))


def dimensions_for_aspect(
    aspect_ratio: str,
    short_side: int = DEFAULT_SHORT_SIDE,
) -> Tuple[int, int]:
    """Return (width, height) pixel dimensions for an aspect ratio string."""
    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        aspect_ratio = DEFAULT_ASPECT_RATIO

    num, den = (int(part) for part in aspect_ratio.split(":"))
    if num <= 0 or den <= 0:
        num, den = 9, 16

    if num >= den:
        height = short_side
        width = int(round(short_side * num / den))
    else:
        width = short_side
        height = int(round(short_side * den / num))

    return _even(width), _even(height)


def frame_size_for_aspect(aspect_ratio: str, short_side: int = DEFAULT_SHORT_SIDE) -> str:
    width, height = dimensions_for_aspect(aspect_ratio, short_side=short_side)
    return f"{width}x{height}"


def dimensions_for_aspect_min_pixels(
    aspect_ratio: str,
    min_pixels: int = SEEDREAM_MIN_PIXELS,
) -> Tuple[int, int]:
    """Return (width, height) with at least ``min_pixels`` total area."""
    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        aspect_ratio = DEFAULT_ASPECT_RATIO

    num, den = (int(part) for part in aspect_ratio.split(":"))
    if num <= 0 or den <= 0:
        num, den = 9, 16

    height = _even(int(math.ceil(math.sqrt(min_pixels * den / num))))
    width = _even(int(math.ceil(height * num / den)))
    while width * height < min_pixels:
        if width <= height:
            width += 2
        else:
            height += 2
    return width, height


def image_size_for_aspect(
    aspect_ratio: str,
    min_pixels: int = SEEDREAM_MIN_PIXELS,
) -> str:
    """Seedream-compatible WxH size that preserves the selected aspect ratio."""
    width, height = dimensions_for_aspect_min_pixels(aspect_ratio, min_pixels=min_pixels)
    return f"{width}x{height}"


def frame_image_size_for_resolution(
    aspect_ratio: str,
    resolution: str = DEFAULT_VIDEO_RESOLUTION,
) -> str:
    """Keyframe size aligned to video output (e.g. 480p → 852x480 for 16:9)."""
    short_side = video_short_side_for_resolution(resolution)
    return frame_size_for_aspect(aspect_ratio, short_side=short_side)


def scene_image_size_for_aspect(aspect_ratio: str) -> str:
    """Scene anchor / shot keyframes at Seedream API minimum for the aspect ratio."""
    return image_size_for_aspect(aspect_ratio)


def dimensions_for_turnaround_min_pixels(
    min_pixels: int = SEEDREAM_MIN_PIXELS,
) -> Tuple[int, int]:
    """3:1 wide turnaround sheet (front | side | back) meeting Seedream minimum area."""
    height = _even(int(math.ceil(math.sqrt(min_pixels / 3))))
    width = _even(height * 3)
    while width * height < min_pixels:
        height += 2
        width = _even(height * 3)
    return width, height


def portrait_turnaround_size(min_pixels: int = SEEDREAM_MIN_PIXELS) -> str:
    """Wide turnaround sheet: front | side | back panels in one image."""
    width, height = dimensions_for_turnaround_min_pixels(min_pixels)
    return f"{width}x{height}"


def portrait_view_size(min_pixels: int = SEEDREAM_MIN_PIXELS) -> str:
    """Single full-body portrait view (square, API minimum)."""
    return image_size_for_aspect("1:1", min_pixels=min_pixels)


def concat_dimensions_for_aspect(
    aspect_ratio: str,
    short_side: int = DEFAULT_SHORT_SIDE,
) -> Tuple[int, int]:
    return dimensions_for_aspect(aspect_ratio, short_side=short_side)


def video_short_side_for_resolution(resolution: str) -> int:
    """Map Seedance resolution label to concat/output short side in pixels."""
    mapping = {"480p": 480, "720p": 720, "1080p": 1080}
    return mapping.get((resolution or DEFAULT_VIDEO_RESOLUTION).lower(), 720)


def resolve_max_shots_for_duration(episode_duration: int) -> Optional[int]:
    """≤15s → one Seedance clip; longer targets use multi-shot + concat."""
    if episode_duration <= 0:
        return None
    if episode_duration <= SEEDANCE_SINGLE_CLIP_MAX_SECONDS:
        return 1
    return max(1, min(3, episode_duration // 5))


def seedance_shot_duration(total_seconds: int, shot_count: int) -> int:
    """Map target length to a Seedance-supported duration (4/5/10/15s)."""
    if shot_count <= 0:
        return 5
    if total_seconds <= 0:
        return 5
    if shot_count == 1 and total_seconds <= SEEDANCE_SINGLE_CLIP_MAX_SECONDS:
        if total_seconds in SEEDANCE_SUPPORTED_DURATIONS:
            return total_seconds
        return min(SEEDANCE_SUPPORTED_DURATIONS, key=lambda d: abs(d - total_seconds))
    per_shot = total_seconds / shot_count
    return min(SEEDANCE_SUPPORTED_DURATIONS, key=lambda d: abs(d - per_shot))


def parse_aspect_ratio(user_requirement: str, default: str = DEFAULT_ASPECT_RATIO) -> str:
    text = user_requirement or ""
    match = re.search(r"Aspect ratio:\s*(\d+:\d+)", text, re.IGNORECASE)
    if match:
        ratio = match.group(1)
        if ratio in SUPPORTED_ASPECT_RATIOS:
            return ratio
    return default if default in SUPPORTED_ASPECT_RATIOS else DEFAULT_ASPECT_RATIO


def resolve_aspect_ratio(
    user_requirement: str = "",
    explicit: Optional[str] = None,
    default: str = DEFAULT_ASPECT_RATIO,
) -> str:
    """Prefer explicit API param, then user_requirement text, then default."""
    if explicit and explicit in SUPPORTED_ASPECT_RATIOS:
        return explicit
    parsed = parse_aspect_ratio(user_requirement, default=default)
    return parsed


def aspect_ratio_llm_hint(aspect_ratio: str) -> str:
    """Explicit orientation wording for LLM prompts (avoid 16:9竖屏 confusion)."""
    ratio = aspect_ratio if aspect_ratio in SUPPORTED_ASPECT_RATIOS else DEFAULT_ASPECT_RATIO
    if ratio == "16:9":
        return (
            "Video format: 16:9 landscape horizontal (宽屏横屏). "
            "Do NOT call this vertical, portrait, or 竖屏."
        )
    if ratio == "9:16":
        return (
            "Video format: 9:16 vertical portrait (竖屏). "
            "Do NOT call this landscape, horizontal, or 横屏."
        )
    num, den = (int(part) for part in ratio.split(":"))
    if num >= den:
        return (
            f"Video format: {ratio} landscape (width >= height). "
            "Do NOT describe as vertical/竖屏."
        )
    return (
        f"Video format: {ratio} portrait (height > width). "
        "Do NOT describe as landscape/横屏."
    )


def sanitize_polished_script(text: str, aspect_ratio: str = "") -> str:
    """Strip LLM meta preamble and fix common wrong aspect-ratio labels."""
    import re

    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned

    # Drop role/meta intro before the first scene/shot marker.
    scene_markers = (
        "**SCENE",
        "SCENE ",
        "场景",
        "**场景",
        "SHOT ",
        "**SHOT",
    )
    for marker in scene_markers:
        idx = cleaned.find(marker)
        if 0 < idx <= 400:
            cleaned = cleaned[idx:].lstrip()
            break

    # Remove a leading horizontal rule left after stripping meta.
    cleaned = re.sub(r"^---+\s*", "", cleaned, count=1)

    ratio = aspect_ratio if aspect_ratio in SUPPORTED_ASPECT_RATIOS else ""
    if ratio == "16:9":
        cleaned = re.sub(r"16\s*[:：]\s*9\s*竖屏", "16:9横屏", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"16\s*[:：]\s*9\s*vertical", "16:9 landscape", cleaned, flags=re.IGNORECASE)
    elif ratio == "9:16":
        cleaned = re.sub(r"9\s*[:：]\s*16\s*横屏", "9:16竖屏", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"9\s*[:：]\s*16\s*landscape", "9:16 portrait", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def text_looks_chinese(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text or "")
