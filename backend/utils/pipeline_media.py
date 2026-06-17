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
# GPUGEEK / Volcengine Seedream minimum output area (e.g. 1920x1920)
SEEDREAM_MIN_PIXELS = 3_686_400


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


def concat_dimensions_for_aspect(
    aspect_ratio: str,
    short_side: int = DEFAULT_SHORT_SIDE,
) -> Tuple[int, int]:
    return dimensions_for_aspect(aspect_ratio, short_side=short_side)


def video_short_side_for_resolution(resolution: str) -> int:
    """Map Seedance resolution label to concat/output short side in pixels."""
    mapping = {"480p": 480, "720p": 720, "1080p": 1080}
    return mapping.get((resolution or DEFAULT_VIDEO_RESOLUTION).lower(), 720)


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
