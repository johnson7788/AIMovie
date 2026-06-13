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

# Used in Seedance video prompts — can stay strongly cinematic.
LIVE_ACTION_VIDEO_DESCRIPTIONS: Dict[str, str] = {
    "cinematic": (
        "Live-action cinematic film footage, photorealistic, natural human skin and hair, "
        "professional cinematography, dramatic lighting, shallow depth of field"
    ),
    "realistic": (
        "Photorealistic live-action footage, natural colors, realistic human proportions, "
        "film camera look, authentic textures"
    ),
}

# Used in Seedream reference images — avoid looking like real-person photos to reduce I2V blocks.
LIVE_ACTION_REFERENCE_DESCRIPTIONS: Dict[str, str] = {
    "cinematic": (
        "Cinematic film still of a fictional virtual actor on a movie set, "
        "natural proportions, subtle film grain and color grading, dramatic movie lighting, "
        "shallow depth of field — looks like a movie frame, not a studio headshot, "
        "not a smartphone selfie, not an ID or stock portrait"
    ),
    "realistic": (
        "Live-action film still of a fictional virtual actor, natural skin texture with "
        "cinematic color grading, realistic movie lighting — clearly a created character "
        "in a staged scene, not a real-person photograph or news image"
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

# Appended to every portrait / storyboard frame used later as Seedance reference input.
SEEDANCE_REFERENCE_GUARDRAIL = (
    "Reference image for AI video generation: depict a clearly fictional virtual actor "
    "in a staged film scene. Not a photograph of a real celebrity, public figure, "
    "news subject, passport photo, or stock portrait."
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
    """Style phrase for Seedream portraits / frames that become Seedance reference images."""
    key = _normalize_style_key(style)
    if is_live_action_style(style):
        base = LIVE_ACTION_REFERENCE_DESCRIPTIONS.get(
            key, LIVE_ACTION_REFERENCE_DESCRIPTIONS["cinematic"]
        )
        return f"{base}. {SEEDANCE_REFERENCE_GUARDRAIL}"
    base = ILLUSTRATED_DESCRIPTIONS.get(key, ILLUSTRATED_DESCRIPTIONS["storybook"])
    return f"{base}. {ILLUSTRATED_IMAGE_SUFFIX}"


def expand_video_style_prompt(style: str) -> str:
    """Style phrase appended to Seedance video prompts."""
    key = _normalize_style_key(style)
    if is_live_action_style(style):
        return LIVE_ACTION_VIDEO_DESCRIPTIONS.get(
            key, LIVE_ACTION_VIDEO_DESCRIPTIONS["cinematic"]
        )
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
