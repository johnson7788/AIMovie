"""Generate actor portrait + three-view turnaround images.

Wraps CharacterPortraitsGenerator so an actor (with a free-text description and
a species type) can be turned into a front portrait and a 3-view turnaround
sheet. The species type only nudges the prompt — the visual identity comes from
the actor's ``remarks`` description, so "其它" (non-human / non-animal) needs no
special handling beyond the description.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

from agents.character_portraits_generator import CharacterPortraitsGenerator
from interfaces import CharacterInScene


# species_type -> prompt hint (matches WEBCONFIG enum: 1 人类 / 2 动物 / 3 其他)
_SPECIES_HINT = {
    1: " The subject is a human being with natural human anatomy.",
    2: " The subject is an animal/creature with non-human anatomy.",
    3: (
        " The subject is a non-human, non-animal being (such as a robot, mech, "
        "monster, spirit, or fantasy creature). Render strictly from the "
        "description without assuming human anatomy."
    ),
}


def _to_int(value) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _character_from_actor(actor: dict) -> CharacterInScene:
    hint = _SPECIES_HINT.get(_to_int(actor.get("species_type")), "")
    features = (actor.get("remarks") or "").strip()
    return CharacterInScene(
        idx=0,
        identifier_in_scene=(actor.get("name") or "character"),
        is_visible=True,
        static_features=features + hint,
        dynamic_features="",
    )


def _image_kwargs(image_generator, *, portrait: bool, reference_path: Optional[str]) -> dict:
    kwargs: dict = {"reference_image_paths": [reference_path] if reference_path else []}
    name = type(image_generator).__name__.lower()
    if "nanobanana" in name:
        kwargs["aspect_ratio"] = "3:4" if portrait else "16:9"
    else:
        kwargs["size"] = "896x1152" if portrait else "1600x900"
    return kwargs


async def generate_actor_portraits(
    *,
    actor: dict,
    image_generator,
    save_dir: str,
    url_prefix: str,
    want_image: bool = True,
    want_three_view: bool = True,
    reference_path: Optional[str] = None,
    style: str = "cinematic",
) -> dict:
    """Generate the requested actor images and persist them under ``save_dir``.

    Returns a dict that may contain ``headimg`` and/or ``three_view_image`` URLs
    (``url_prefix`` + filename), only for the views that were requested.
    """
    os.makedirs(save_dir, exist_ok=True)
    gen = CharacterPortraitsGenerator(image_generator)
    character = _character_from_actor(actor)
    actor_id = actor.get("id") or uuid.uuid4().hex
    results: dict = {}

    if want_image:
        out = await gen.generate_front_portrait(
            character,
            style,
            image_gen_kwargs=_image_kwargs(image_generator, portrait=True, reference_path=reference_path),
        )
        fname = f"{actor_id}_front_{uuid.uuid4().hex[:8]}.png"
        out.save(os.path.join(save_dir, fname))
        results["headimg"] = f"{url_prefix}/{fname}"

    if want_three_view:
        out = await gen.generate_turnaround_sheet(
            character,
            style,
            image_gen_kwargs=_image_kwargs(image_generator, portrait=False, reference_path=reference_path),
        )
        fname = f"{actor_id}_3v_{uuid.uuid4().hex[:8]}.png"
        out.save(os.path.join(save_dir, fname))
        results["three_view_image"] = f"{url_prefix}/{fname}"

    return results
