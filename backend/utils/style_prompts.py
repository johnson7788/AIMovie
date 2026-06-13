"""Map UI style ids to image/video prompts that avoid real-person moderation."""

from __future__ import annotations

from typing import Dict

# Seedance I2V rejects reference frames that look like real people.
FICTIONAL_CHARACTER_SUFFIX = (
    "Stylized fictional character illustration only. "
    "Clearly illustrated or animated, not a photograph of a real person."
)

STYLE_DESCRIPTIONS: Dict[str, str] = {
    "cinematic": "Cinematic fictional film still, dramatic lighting, production design",
    "anime": "Anime style, 2D animation, cel-shaded, illustrated characters",
    "storybook": "Storybook picture-book illustration, hand-painted, whimsical, soft colors",
    "realistic": "Stylized cinematic realism of a fictional character, film still, not a real photo",
    "watercolor": "Watercolor illustration, painterly, soft edges, hand-drawn look",
    "3d_render": "3D animated render, Pixar-like fictional character, stylized CGI",
    "pixel_art": "Pixel art illustration, retro game style, clearly non-photographic",
    "comic": "Comic book illustration, inked lines, bold colors, graphic novel style",
}


def _normalize_style_key(style: str) -> str:
    return (style or "").strip().lower().replace(" ", "_").replace("-", "_")


def expand_style_prompt(style: str) -> str:
    """Return a rich, moderation-safe style phrase for image generation."""
    key = _normalize_style_key(style)
    if key in STYLE_DESCRIPTIONS:
        base = STYLE_DESCRIPTIONS[key]
    elif key:
        base = style.strip()
    else:
        base = STYLE_DESCRIPTIONS["cinematic"]
    return f"{base}. {FICTIONAL_CHARACTER_SUFFIX}"


def is_real_person_rejection(message: str) -> bool:
    lower = (message or "").lower()
    markers = (
        "real person",
        "realistic human",
        "contains real person",
        "input image may contain",
    )
    return any(marker in lower for marker in markers)
