import logging
import os
import aiohttp
from typing import List, Optional
from tenacity import retry, stop_after_attempt
from utils.retry import after_func
from utils.image import image_path_to_b64
from utils.rate_limiter import RateLimiter
from interfaces.image_output import ImageOutput


def _map_size(size: Optional[str]) -> str:
    """Map pixel size strings to Volcengine Seedream size format.
    Volcengine uses '2K', '4K' etc."""
    if size is None:
        return "2K"
    mapping = {
        "512x512": "2K",
        "1024x1024": "2K",
        "1600x900": "2K",
    }
    return mapping.get(size, size)


class ImageGeneratorDoubaoSeedreamVolcengineAPI:
    def __init__(
        self,
        api_key: str = "",
        model: str = "doubao-seedream-5-0-260128",
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if not api_key:
            api_key = os.environ.get("ARK_API_KEY", "")
        self.api_key = api_key
        self.base_url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        self.model = model
        self.rate_limiter = rate_limiter

    @retry(stop=stop_after_attempt(3), after=after_func)
    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
        size: Optional[str] = None,
        **kwargs,
    ) -> ImageOutput:
        logging.info(f"Calling {self.model} to generate image...")

        if self.rate_limiter:
            await self.rate_limiter.acquire()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": _map_size(size),
            "output_format": "png",
            "watermark": False,
        }

        if len(reference_image_paths) > 0:
            payload["image"] = image_path_to_b64(reference_image_paths[0])

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=300)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logging.info(f"Sending image generation request to {self.model} (timeout=300s)...")
                async with session.post(self.base_url, json=payload, headers=headers) as response:
                    logging.info(f"Image generation HTTP status: {response.status}")
                    response_json = await response.json()
                    logging.debug(f"Image generation response: {response_json}")
        except aiohttp.ClientTimeout:
            logging.error(f"Image generation request timed out after 300s")
            raise TimeoutError(f"Image generation request to {self.model} timed out after 300s")
        except Exception as e:
            logging.error(f"Error occurred while generating image: {e}")
            raise e

        if "error" in response_json:
            logging.error(f"Image generation API error: {response_json['error']}")
            raise ValueError(f"Image generation failed: {response_json['error']}")

        if "data" not in response_json or not response_json["data"]:
            logging.error(f"Unexpected response format: {response_json}")
            raise ValueError(f"Unexpected response format: {response_json}")

        data = response_json['data'][0]['url']
        return ImageOutput(fmt="url", ext="png", data=data)
