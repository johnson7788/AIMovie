"""Agnes AI Image Generator — OpenAI-compatible Images API.

Endpoint: POST https://apihub.agnes-ai.com/v1/images/generations
Model:    agnes-image-2.1-flash
Docs:     https://www.agnes-ai.com/doc/agnes-image-21-flash
"""

import logging
import os
import asyncio
from typing import List, Optional

import aiohttp

from interfaces.image_output import ImageOutput
from utils.image import image_path_to_b64
from utils.rate_limiter import RateLimiter


# Map common AIMovie size strings to Agnes-supported sizes.
# Agnes accepts arbitrary WxH; these keep a 16:9 / 9:16 / 1:1 ratio.
_SIZE_MAP = {
    "1600x900":  "1344x768",   # 16:9
    "900x1600":  "768x1344",   # 9:16
    "1024x1024": "1024x1024",  # 1:1
    "512x512":   "1024x1024",  # upscale square
    "2048x2048": "1024x1024",  # clamp to max
}
_DEFAULT_SIZE = "1344x768"

# Map aspect_ratio kwarg to a size string.
_ASPECT_SIZE_MAP = {
    "16:9":  "1344x768",
    "9:16":  "768x1344",
    "1:1":   "1024x1024",
    "4:3":   "1024x768",
    "3:4":   "768x1024",
}


def _resolve_size(size: Optional[str], aspect_ratio: Optional[str]) -> str:
    """Return a WxH string suitable for Agnes Image API."""
    if size and size in _SIZE_MAP:
        return _SIZE_MAP[size]
    if size and "x" in size:
        return size
    if aspect_ratio and aspect_ratio in _ASPECT_SIZE_MAP:
        return _ASPECT_SIZE_MAP[aspect_ratio]
    return _DEFAULT_SIZE


class ImageGeneratorAgnesAPI:
    """Generates images via the Agnes AI OpenAI-compatible Images API."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "agnes-image-2.1-flash",
        base_url: str = "https://apihub.agnes-ai.com/v1",
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if not api_key:
            api_key = os.environ.get("AGNES_API_KEY", "")
        if not api_key:
            raise ValueError(
                "Agnes AI API key is required. "
                "Set the AGNES_API_KEY environment variable or pass api_key=..."
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.rate_limiter = rate_limiter

    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
        size: Optional[str] = None,
        aspect_ratio: Optional[str] = "16:9",
        **kwargs,
    ) -> ImageOutput:
        """Generate a single image.

        - Text-to-image: no reference_image_paths
        - Image-to-image: pass local file paths in reference_image_paths
        """
        resolved_size = _resolve_size(size, aspect_ratio)
        logging.info(
            "Calling Agnes %s to generate image (size=%s, refs=%d)...",
            self.model, resolved_size, len(reference_image_paths),
        )

        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Build request payload
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "size": resolved_size,
        }

        # Use URL output format by default
        extra_body: dict = {"response_format": "url"}

        # Image-to-image: attach reference images as Data URIs
        if reference_image_paths:
            extra_body["image"] = [
                image_path_to_b64(path, mime=True) for path in reference_image_paths
            ]

        payload["extra_body"] = extra_body

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        endpoint = f"{self.base_url}/images/generations"
        timeout = aiohttp.ClientTimeout(total=360)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                logging.info("Agnes image API HTTP status: %d", resp.status)
                response_json = await resp.json()

                if resp.status >= 400:
                    error_detail = (
                        response_json.get("error", {}).get("message")
                        if isinstance(response_json.get("error"), dict)
                        else response_json.get("error") or str(response_json)
                    )
                    logging.error("Agnes image API error: %s", error_detail)
                    raise ValueError(f"Agnes image generation failed (HTTP {resp.status}): {error_detail}")

        # Parse response — OpenAI-compatible format
        data = response_json.get("data")
        if not data or not isinstance(data, list):
            raise ValueError(f"Unexpected Agnes image response format: {response_json}")

        first = data[0]
        image_url = first.get("url")
        b64_json = first.get("b64_json")

        if image_url:
            logging.info("Agnes image generated (URL): %s", image_url[:120])
            return ImageOutput(fmt="url", ext="png", data=image_url)
        elif b64_json:
            logging.info("Agnes image generated (base64), length=%d", len(b64_json))
            return ImageOutput(fmt="b64", ext="png", data=b64_json)
        else:
            raise ValueError(f"No image data in Agnes response: {first}")
