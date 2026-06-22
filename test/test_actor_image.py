"""Unit tests for actor portrait generation orchestration.

These are self-contained: they inject a fake image generator, so they need no
running server and no image-generation API key.
"""
import asyncio
import os
import sys

from PIL import Image

BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from interfaces import ImageOutput  # noqa: E402
import actor_image  # noqa: E402


class FakeGenerator:
    """Records calls and returns a tiny white PIL image."""

    def __init__(self):
        self.calls = []

    async def generate_single_image(self, prompt, reference_image_paths=None, **kwargs):
        self.calls.append({
            "prompt": prompt,
            "reference_image_paths": reference_image_paths,
            **kwargs,
        })
        return ImageOutput(fmt="pil", ext="png", data=Image.new("RGB", (8, 8), "white"))


def _run(coro):
    return asyncio.run(coro)


def test_generate_both_views(tmp_path):
    gen = FakeGenerator()
    actor = {"id": "actor1", "name": "阿狗", "remarks": "金毛犬", "species_type": 2}
    results = _run(actor_image.generate_actor_portraits(
        actor=actor, image_generator=gen, save_dir=str(tmp_path),
        url_prefix="/api/uploads/actor/generated",
        want_image=True, want_three_view=True,
    ))
    assert results["headimg"].startswith("/api/uploads/actor/generated/")
    assert results["three_view_image"].startswith("/api/uploads/actor/generated/")
    for url in results.values():
        assert (tmp_path / url.split("/")[-1]).exists()
    assert len(gen.calls) == 2


def test_only_three_view(tmp_path):
    gen = FakeGenerator()
    actor = {"id": "a2", "name": "机器人", "remarks": "银色机甲", "species_type": 3}
    results = _run(actor_image.generate_actor_portraits(
        actor=actor, image_generator=gen, save_dir=str(tmp_path),
        url_prefix="/api/uploads/actor/generated",
        want_image=False, want_three_view=True,
    ))
    assert "headimg" not in results
    assert "three_view_image" in results
    assert len(gen.calls) == 1


def test_species_hint_other(tmp_path):
    """species_type=3 (其他) injects a non-human/non-animal hint into the prompt."""
    gen = FakeGenerator()
    actor = {"id": "a3", "name": "外星人", "remarks": "三只眼", "species_type": 3}
    _run(actor_image.generate_actor_portraits(
        actor=actor, image_generator=gen, save_dir=str(tmp_path),
        url_prefix="/x", want_image=True, want_three_view=False,
    ))
    assert "non-human, non-animal" in gen.calls[0]["prompt"]
    assert "三只眼" in gen.calls[0]["prompt"]


def test_species_hint_human(tmp_path):
    gen = FakeGenerator()
    actor = {"id": "a5", "name": "小明", "remarks": "短发男青年", "species_type": 1}
    _run(actor_image.generate_actor_portraits(
        actor=actor, image_generator=gen, save_dir=str(tmp_path),
        url_prefix="/x", want_image=True, want_three_view=False,
    ))
    assert "human being" in gen.calls[0]["prompt"]


def test_reference_passed(tmp_path):
    gen = FakeGenerator()
    ref = tmp_path / "ref.png"
    Image.new("RGB", (4, 4), "red").save(ref)
    actor = {"id": "a4", "name": "x", "remarks": "y", "species_type": 1}
    _run(actor_image.generate_actor_portraits(
        actor=actor, image_generator=gen, save_dir=str(tmp_path),
        url_prefix="/x", want_image=True, want_three_view=False,
        reference_path=str(ref),
    ))
    assert gen.calls[0]["reference_image_paths"] == [str(ref)]


def test_no_reference_passes_empty_list(tmp_path):
    gen = FakeGenerator()
    actor = {"id": "a6", "name": "x", "remarks": "y", "species_type": 1}
    _run(actor_image.generate_actor_portraits(
        actor=actor, image_generator=gen, save_dir=str(tmp_path),
        url_prefix="/x", want_image=True, want_three_view=False,
    ))
    assert gen.calls[0]["reference_image_paths"] == []
