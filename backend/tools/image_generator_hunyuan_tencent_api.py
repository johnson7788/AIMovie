# Tencent Hunyuan Image Generation API
# Docs: https://cloud.tencent.com/document/product/1729

import asyncio
import logging
import os
from typing import List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt

from interfaces.image_output import ImageOutput
from utils.rate_limiter import RateLimiter
from utils.retry import after_func


class ImageGeneratorHunyuanTencentAPI:
    def __init__(
        self,
        api_key: str = "",
        model: str = "hy-image-v3.0",
        rate_limiter: Optional[RateLimiter] = None,
    ):
        if not api_key:
            api_key = os.environ.get("HUNYUAN_VISION_API_KEY", "")
        self.api_key = api_key
        self.model = model
        self.rate_limiter = rate_limiter
        self.submit_url = "https://tokenhub.tencentmaas.com/v1/api/image/submit"
        self.query_url = "https://tokenhub.tencentmaas.com/v1/api/image/query"
        self._poll_interval = 2  # seconds between status checks
        self._max_wait = 300     # max wait time in seconds

    @retry(stop=stop_after_attempt(3), after=after_func)
    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
        size: Optional[str] = None,
        **kwargs,
    ) -> ImageOutput:
        logging.info(f"Calling Hunyuan {self.model} to generate image...")

        if self.rate_limiter:
            await self.rate_limiter.acquire()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Step 1: Submit the generation task
        submit_payload = {
            "model": self.model,
            "prompt": prompt,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.submit_url, json=submit_payload, headers=headers
            ) as resp:
                submit_json = await resp.json()
                logging.debug(f"Hunyuan submit response: {submit_json}")

            if "error" in submit_json:
                logging.error(f"Hunyuan submit error: {submit_json['error']}")
                raise ValueError(f"Hunyuan image submit failed: {submit_json['error']}")

            task_id = submit_json.get("id")
            if not task_id:
                logging.error(f"Hunyuan submit: no id in response: {submit_json}")
                raise ValueError(f"Hunyuan image submit failed: no task id returned")

            # Step 2: Poll for result
            query_payload = {
                "model": self.model,
                "id": task_id,
            }

            elapsed = 0
            while elapsed < self._max_wait:
                await asyncio.sleep(self._poll_interval)
                elapsed += self._poll_interval

                async with session.post(
                    self.query_url, json=query_payload, headers=headers
                ) as resp:
                    query_json = await resp.json()
                    logging.debug(f"Hunyuan query response (elapsed={elapsed}s): {query_json}")

                if "error" in query_json:
                    logging.error(f"Hunyuan query error: {query_json['error']}")
                    raise ValueError(f"Hunyuan image query failed: {query_json['error']}")

                status = query_json.get("status", "")
                if status in ("completed", "success", "done"):
                    image_url = query_json.get("url") or query_json.get("image_url")
                    if image_url:
                        return ImageOutput(fmt="url", ext="png", data=image_url)
                    # Some APIs return images in results array
                    results = query_json.get("results", [])
                    if results and results[0].get("url"):
                        return ImageOutput(fmt="url", ext="png", data=results[0]["url"])
                    logging.error(f"Hunyuan query: no image url in completed response: {query_json}")
                    raise ValueError("Hunyuan image query: task completed but no image url found")

                if status in ("failed", "error"):
                    error_msg = query_json.get("error", "unknown error")
                    logging.error(f"Hunyuan task {task_id} failed: {error_msg}")
                    raise ValueError(f"Hunyuan image generation failed: {error_msg}")

            # Timeout
            raise TimeoutError(
                f"Hunyuan image generation timed out after {self._max_wait}s (task_id={task_id})"
            )
