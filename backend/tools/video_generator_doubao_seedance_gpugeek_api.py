import logging
import os
import time
import aiohttp
import asyncio
from typing import Any, Dict, List, Literal
from interfaces.video_output import VideoOutput
from utils.image import image_path_to_b64


def _extract_output(response_json: Dict[str, Any]) -> str:
    """Extract the output URL from a prediction response."""
    output = response_json.get("output")
    if isinstance(output, list) and len(output) > 0:
        return output[0]
    elif isinstance(output, str):
        return output
    raise ValueError(f"Unexpected output format: {output}")


class VideoGeneratorDoubaoSeedanceGPUGEEKAPI:
    def __init__(
        self,
        api_key: str = "",
        t2v_model: str = "Volcengine/Doubao-Seedance-2.0-fast",
        ff2v_model: str = "Volcengine/Doubao-Seedance-2.0-fast",
        flf2v_model: str = "Volcengine/Doubao-Seedance-2.0-fast",
    ):
        if not api_key:
            api_key = os.environ.get("GPUGEEK", "")
        self.api_key = api_key
        self.base_url = "https://api.gpugeek.com/predictions"
        self.t2v_model = t2v_model
        self.ff2v_model = ff2v_model
        self.flf2v_model = flf2v_model

    async def _create_prediction(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        duration: Literal[4, 5, 10] = 5,
    ) -> Dict[str, Any]:
        if len(reference_image_paths) == 0:
            model = self.t2v_model
        elif len(reference_image_paths) == 1:
            model = self.ff2v_model
        elif len(reference_image_paths) == 2:
            model = self.flf2v_model
        else:
            raise ValueError("reference_image_paths must contain 0, 1, or 2 images.")

        logging.info(f"Sending video generation request to GPUGEEK {model}...")

        resolution_map = {"480p": "480p", "720p": "720p", "1080p": "1080p"}
        ratio_map = {"16:9": "adaptive", "9:16": "adaptive", "1:1": "adaptive"}

        input_data = {
            "task_type": "reference",
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution_map.get(resolution, "720p"),
            "ratio": ratio_map.get(aspect_ratio, "adaptive"),
            "watermark": False,
        }

        if len(reference_image_paths) >= 1:
            input_data["images"] = [
                image_path_to_b64(path, mime=True) for path in reference_image_paths
            ]

        payload = {
            "model": model,
            "input": input_data,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=300)  # 5 min timeout for task creation
        while True:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(self.base_url, headers=headers, json=payload) as response:
                        logging.info(f"Video create request HTTP status: {response.status}")
                        response_json = await response.json()
                        logging.debug(f"Create video prediction response: {response_json}")
                        if "error" in response_json:
                            logging.error(f"Video create API error: {response_json['error']}")
                            raise ValueError(f"Video creation failed: {response_json['error']}")
                        return response_json
            except (aiohttp.ClientTimeout, asyncio.TimeoutError):
                logging.error(f"Video create request timed out. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue
            except Exception as e:
                logging.error(f"Error creating video generation task: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue

    async def _poll_prediction(self, prediction_id: str, headers: dict) -> str:
        url = f"{self.base_url}/{prediction_id}"
        max_polls = 600  # 20 minutes max
        start_time = time.time()
        last_log_time = start_time
        LOG_INTERVAL = 30  # only log progress every 30 seconds

        timeout = aiohttp.ClientTimeout(total=30)  # 30s timeout per poll
        for _ in range(max_polls):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        response_json = await response.json()
                        logging.debug(f"Poll response: {response_json}")
            except (aiohttp.ClientTimeout, asyncio.TimeoutError):
                logging.warning(f"Poll request timed out. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue
            except Exception as e:
                logging.error(f"Error polling video task: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue

            status = response_json.get("status")
            if status == "succeeded":
                elapsed = time.time() - start_time
                video_url = _extract_output(response_json)
                logging.info(f"Video generation completed (elapsed: {elapsed:.0f}s). URL: {video_url}")
                return video_url
            elif status == "failed":
                elapsed = time.time() - start_time
                error_msg = response_json.get("error", "Unknown error")
                logging.error(f"Video generation failed after {elapsed:.0f}s: {error_msg}")
                raise ValueError(f"Video generation failed: {error_msg}")
            else:
                now = time.time()
                elapsed = now - start_time
                if now - last_log_time >= LOG_INTERVAL:
                    logging.info(f"Video generation in progress (status={status}, elapsed: {elapsed:.0f}s)...")
                    last_log_time = now
                await asyncio.sleep(2)
                continue

        raise TimeoutError(f"Video generation timed out after {max_polls} polls")

    async def generate_single_video(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        duration: Literal[4, 5, 10] = 5,
        **kwargs,
    ) -> VideoOutput:
        response_json = await self._create_prediction(
            prompt, reference_image_paths, resolution, aspect_ratio, duration
        )

        # GPUGeek may return the result synchronously
        status = response_json.get("status")
        if status == "succeeded":
            video_url = _extract_output(response_json)
            logging.info(f"Video generation completed synchronously. URL: {video_url}")
            return VideoOutput(fmt="url", ext="mp4", data=video_url)

        if status == "failed":
            error_msg = response_json.get("error", "Unknown error")
            logging.error(f"Video generation failed: {error_msg}")
            raise ValueError(f"Video generation failed: {error_msg}")

        # Async: poll for completion
        task_id = response_json["id"]
        logging.info(f"Video generation task created. ID: {task_id}, status: {status}")
        video_url = await self._poll_prediction(task_id, {
            "Authorization": f"Bearer {self.api_key}",
        })
        return VideoOutput(fmt="url", ext="mp4", data=video_url)
