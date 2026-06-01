import logging
import os
import aiohttp
import asyncio
from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt
from utils.retry import after_func
from utils.image import image_path_to_b64
from interfaces.image_output import ImageOutput


def _map_size(size: Optional[str]) -> str:
    """Map pixel size strings to GPUGEEK Seedream size format ('2K', '4K')."""
    if size is None:
        return "2K"
    mapping = {
        "512x512": "2K",
        "1024x1024": "2K",
        "1600x900": "2K",
        "2048x2048": "4K",
    }
    return mapping.get(size, size)


def _extract_output(response_json: Dict[str, Any]) -> str:
    """Extract the output URL from a prediction response."""
    output = response_json.get("output")
    if isinstance(output, list) and len(output) > 0:
        return output[0]
    elif isinstance(output, str):
        return output
    raise ValueError(f"Unexpected output format: {output}")


class ImageGeneratorDoubaoSeedreamGPUGEEKAPI:
    def __init__(
        self,
        api_key: str = "",
        model: str = "Volcengine/Doubao-Seedream-5.0-lite",
    ):
        if not api_key:
            api_key = os.environ.get("GPUGEEK", "")
        self.api_key = api_key
        self.base_url = "https://api.gpugeek.com/predictions"
        self.model = model

    @retry(stop=stop_after_attempt(3), after=after_func)
    async def generate_single_image(
        self,
        prompt: str,
        reference_image_paths: List[str] = [],
        size: Optional[str] = None,
        **kwargs,
    ) -> ImageOutput:
        logging.info(f"Calling GPUGEEK {self.model} to generate image...")

        input_data = {
            "prompt": prompt,
            "size": _map_size(size),
            "output_format": "png",
            "watermark": False,
        }

        if len(reference_image_paths) > 0:
            input_data["images"] = [
                image_path_to_b64(path, mime=True) for path in reference_image_paths
            ]

        payload = {
            "model": self.model,
            "input": input_data,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Create prediction — GPUGeek returns the result synchronously
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=headers) as response:
                    response_json = await response.json()
                    logging.debug(f"Create prediction response: {response_json}")
        except Exception as e:
            logging.error(f"Error creating image prediction: {e}")
            raise e

        # Check if the create response already contains the completed result
        status = response_json.get("status")
        if status == "succeeded":
            image_url = _extract_output(response_json)
            logging.info(f"Image generation completed synchronously. URL: {image_url}")
            return ImageOutput(fmt="url", ext="png", data=image_url)

        if status == "failed":
            error_msg = response_json.get("error", "Unknown error")
            logging.error(f"Image generation failed: {error_msg}")
            raise ValueError(f"Image generation failed: {error_msg}")

        # Fallback: poll for async completion
        prediction_id = response_json.get("id")
        if not prediction_id:
            logging.error(f"No prediction ID in response: {response_json}")
            raise ValueError(f"Failed to create image prediction: {response_json}")

        logging.info(f"Image prediction created. ID: {prediction_id}, status: {status}")
        image_url = await self._poll_prediction(prediction_id, headers)
        return ImageOutput(fmt="url", ext="png", data=image_url)

    async def _poll_prediction(self, prediction_id: str, headers: dict) -> str:
        url = f"{self.base_url}/{prediction_id}"
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        response_json = await response.json()
                        logging.debug(f"Poll response: {response_json}")
            except Exception as e:
                logging.error(f"Error polling prediction: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue

            status = response_json.get("status")
            if status == "succeeded":
                image_url = _extract_output(response_json)
                logging.info(f"Image generation completed. URL: {image_url}")
                return image_url
            elif status == "failed":
                error_msg = response_json.get("error", "Unknown error")
                logging.error(f"Image generation failed: {error_msg}")
                raise ValueError(f"Image generation failed: {error_msg}")
            else:
                logging.info(f"Image generation status: {status}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue
