import logging
import os
import asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chat_models.base import BaseChatModel
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from tenacity import retry, stop_after_attempt
from interfaces import CharacterInScene, ImageOutput
from langchain_core.messages import HumanMessage, SystemMessage
from utils.retry import after_func
from utils.style_prompts import expand_style_prompt



prompt_template_front = \
"""
Generate a full-body, front-view portrait of character {identifier} based on the following description, with a pure white background. The character should be centered in the image, occupying most of the frame. Gazing straight ahead. Standing with arms relaxed at sides. Natural expression.
Features: {features}
Style: {style}
"""

prompt_template_side = \
"""
Generate a full-body, side-view portrait of character {identifier} based on the provided front-view portrait, with a pure white background. The character should be centered in the image, occupying most of the frame. Facing left. Standing with arms relaxed at sides.

CRITICAL: The character's appearance (facial features, body shape, clothing, colors, proportions) must EXACTLY match the character shown in the front-view reference image. Only the viewing angle should change — the character itself must be IDENTICAL. Every detail of the costume, hairstyle, body type, and color palette must be faithfully replicated from the reference image.

Character features (for identity anchoring):
{features}
Style: {style}
"""

prompt_template_back = \
"""
Generate a full-body, back-view portrait of character {identifier} based on the provided front-view portrait, with a pure white background. The character should be centered in the image, occupying most of the frame. No facial features should be visible.

CRITICAL: The character's appearance (body shape, clothing, colors, proportions, hairstyle from behind) must EXACTLY match the character shown in the front-view reference image. Only the viewing angle should change — the character itself must be IDENTICAL. Every detail of the costume, body type, hair style/color, and color palette must be faithfully replicated from the reference image.

Character features (for identity anchoring):
{features}
Style: {style}
"""

prompt_template_turnaround = \
"""
Generate a character turnaround sheet for character {identifier} with 3 views arranged side-by-side horizontally in a single wide image. Pure white background throughout all panels.

The 3 views must be equally spaced from left to right:
- LEFT panel: FULL-BODY FRONT VIEW — character facing directly forward, arms relaxed at sides, natural expression, centered in frame
- CENTER panel: FULL-BODY SIDE VIEW — character facing left (profile), arms relaxed at sides, centered in frame
- RIGHT panel: FULL-BODY BACK VIEW — character facing away from viewer, no facial features visible, centered in frame

CRITICAL: All 3 panels MUST depict the EXACT SAME character with perfect consistency. Same facial features, same body type, same skin tone, same hairstyle and hair color, same clothing with identical colors and details, same proportions. The ONLY difference between panels is the viewing angle. This is essential — the character must be visually identical across all 3 views.

Character description:
{features}
Style: {style}
"""


class CharacterPortraitsGenerator:
    def __init__(
        self,
        image_generator,
    ):
        self.image_generator = image_generator

    @staticmethod
    def _style_phrase(style: str) -> str:
        return expand_style_prompt(style)
    @retry(stop=stop_after_attempt(3), after=after_func, reraise=True)
    async def generate_front_portrait(
        self,
        character: CharacterInScene,
        style: str,
        image_gen_kwargs: Optional[Dict] = None,
    ) -> ImageOutput:
        features = "(static) " + character.static_features + "; (dynamic) " + character.dynamic_features
        prompt = prompt_template_front.format(
            identifier=character.identifier_in_scene,
            features=features,
            style=self._style_phrase(style),
        )
        gen_kwargs = dict(image_gen_kwargs or {})
        image_output = await self.image_generator.generate_single_image(
            prompt=prompt,
            **gen_kwargs,
        )
        return image_output

    @retry(stop=stop_after_attempt(3), after=after_func, reraise=True)
    async def generate_side_portrait(
        self,
        character: CharacterInScene,
        front_image_path: str,
        style: str,
        image_gen_kwargs: Optional[Dict] = None,
    ) -> ImageOutput:
        features = "(static) " + character.static_features + "; (dynamic) " + character.dynamic_features
        prompt = prompt_template_side.format(
            identifier=character.identifier_in_scene,
            features=features,
            style=self._style_phrase(style),
        )
        gen_kwargs = dict(image_gen_kwargs or {})
        image_output = await self.image_generator.generate_single_image(
            prompt=prompt,
            reference_image_paths=[front_image_path],
            **gen_kwargs,
        )
        return image_output


    @retry(stop=stop_after_attempt(3), after=after_func, reraise=True)
    async def generate_back_portrait(
        self,
        character: CharacterInScene,
        front_image_path: str,
        style: str,
        image_gen_kwargs: Optional[Dict] = None,
    ) -> ImageOutput:
        features = "(static) " + character.static_features + "; (dynamic) " + character.dynamic_features
        prompt = prompt_template_back.format(
            identifier=character.identifier_in_scene,
            features=features,
            style=self._style_phrase(style),
        )
        gen_kwargs = dict(image_gen_kwargs or {})
        image_output = await self.image_generator.generate_single_image(
            prompt=prompt,
            reference_image_paths=[front_image_path],
            **gen_kwargs,
        )
        return image_output

    @retry(stop=stop_after_attempt(3), after=after_func, reraise=True)
    async def generate_turnaround_sheet(
        self,
        character: CharacterInScene,
        style: str,
        image_gen_kwargs: Optional[Dict] = None,
    ) -> ImageOutput:
        """Generate a single 3-view turnaround sheet image.

        Produces one image with front, side, and back views arranged horizontally.
        This ensures character consistency across all views since they originate
        from a single model inference.
        """
        features = "(static) " + character.static_features + "; (dynamic) " + character.dynamic_features
        prompt = prompt_template_turnaround.format(
            identifier=character.identifier_in_scene,
            features=features,
            style=self._style_phrase(style),
        )
        gen_kwargs = dict(image_gen_kwargs or {})
        image_output = await self.image_generator.generate_single_image(
            prompt=prompt,
            **gen_kwargs,
        )
        return image_output