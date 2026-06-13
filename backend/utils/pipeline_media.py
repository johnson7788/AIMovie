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


def text_looks_chinese(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text or "")
