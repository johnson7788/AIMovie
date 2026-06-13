"""Map UI style ids to image/video prompts, balancing look vs Seedance moderation."""

from __future__ import annotations

from typing import Dict

# Styles that should look like live-action / photorealistic humans on screen.
LIVE_ACTION_STYLE_IDS = frozenset({"cinematic", "realistic"})

# Styles that should deliberately look illustrated or animated.
ILLUSTRATED_STYLE_IDS = frozenset({
    "anime",
    "storybook",
    "watercolor",
    "3d_render",
    "pixel_art",
    "comic",
})

LIVE_ACTION_DESCRIPTIONS: Dict[str, str] = {
    "cinematic": (
        "Live-action cinematic film footage, photorealistic, natural human skin and hair, "
        "professional cinematography, dramatic lighting, shallow depth of field"
    ),
    "realistic": (
        "Photorealistic live-action footage, natural colors, realistic human proportions, "
        "film camera look, authentic textures"
    ),
}

ILLUSTRATED_DESCRIPTIONS: Dict[str, str] = {
    "anime": "Anime style, 2D animation, cel-shaded illustrated characters",
    "storybook": "Storybook picture-book illustration, hand-painted, whimsical, soft colors",
    "watercolor": "Watercolor illustration, painterly, soft edges, hand-drawn look",
    "3d_render": "3D animated render, stylized CGI characters",
    "pixel_art": "Pixel art illustration, retro game style",
    "comic": "Comic book illustration, inked lines, bold colors",
}

# Keep reference images on the "fictional production" side for Seedance moderation.
LIVE_ACTION_IMAGE_SUFFIX = (
    "Fictional character in a staged film scene. "
    "AI-generated cinematic imagery, not a real celebrity or news photograph."
)

ILLUSTRATED_IMAGE_SUFFIX = (
    "Fictional illustrated character. Clearly non-photographic stylized art."
)


def _normalize_style_key(style: str) -> str:
    return (style or "").strip().lower().replace(" ", "_").replace("-", "_")


def is_live_action_style(style: str) -> bool:
    key = _normalize_style_key(style)
    if key in ILLUSTRATED_STYLE_IDS:
        return False
    if key in LIVE_ACTION_STYLE_IDS:
        return True
    # Short-drama defaults: users usually expect live-action unless they pick illustration.
    return True


def expand_image_style_prompt(style: str) -> str:
    """Style phrase for Seedream frame / portrait generation."""
    key = _normalize_style_key(style)
    if is_live_action_style(style):
        base = LIVE_ACTION_DESCRIPTIONS.get(key, LIVE_ACTION_DESCRIPTIONS["cinematic"])
        return f"{base}. {LIVE_ACTION_IMAGE_SUFFIX}"
    base = ILLUSTRATED_DESCRIPTIONS.get(key, ILLUSTRATED_DESCRIPTIONS["storybook"])
    return f"{base}. {ILLUSTRATED_IMAGE_SUFFIX}"


def expand_video_style_prompt(style: str) -> str:
    """Style phrase appended to Seedance video prompts."""
    key = _normalize_style_key(style)
    if is_live_action_style(style):
        return LIVE_ACTION_DESCRIPTIONS.get(key, LIVE_ACTION_DESCRIPTIONS["cinematic"])
    return ILLUSTRATED_DESCRIPTIONS.get(key, ILLUSTRATED_DESCRIPTIONS["storybook"])


def expand_style_prompt(style: str) -> str:
    """Backward-compatible alias for image generation."""
    return expand_image_style_prompt(style)


def is_real_person_rejection(message: str) -> bool:
    lower = (message or "").lower()
    markers = (
        "real person",
        "realistic human",
        "contains real person",
        "input image may contain",
    )
    return any(marker in lower for marker in markers)
