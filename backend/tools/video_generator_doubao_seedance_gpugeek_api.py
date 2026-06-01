import logging
import os
import aiohttp
import asyncio
from typing import List, Literal
from interfaces.video_output import VideoOutput
from utils.image import image_path_to_b64


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

    async def create_video_generation_task(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        duration: Literal[4, 5, 10] = 5,
    ) -> str:
        if len(reference_image_paths) == 0:
            model = self.t2v_model
        elif len(reference_image_paths) == 1:
            model = self.ff2v_model
        elif len(reference_image_paths) == 2:
            model = self.flf2v_model
        else:
            raise ValueError("reference_image_paths must contain 0, 1, or 2 images.")

        logging.info(f"Calling GPUGEEK {model} to generate video...")

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

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.base_url, headers=headers, json=payload) as response:
                        response_json = await response.json()
                        logging.debug(f"Create video prediction response: {response_json}")
                        task_id = response_json["id"]
            except Exception as e:
                logging.error(f"Error creating video generation task: {e}. Retrying in 1 second...")
                await asyncio.sleep(1)
                continue
            break

        logging.info(f"Video generation task created. Task ID: {task_id}")
        return task_id

    async def query_video_generation_task(self, task_id: str) -> str:
        url = f"{self.base_url}/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        response_json = await response.json()
                        logging.debug(f"Query response: {response_json}")
            except Exception as e:
                logging.error(f"Error querying video task: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue

            status = response_json.get("status")
            if status == "succeeded":
                output = response_json.get("output")
                if isinstance(output, list):
                    video_url = output[0]
                elif isinstance(output, str):
                    video_url = output
                else:
                    raise ValueError(f"Unexpected output format: {output}")
                logging.info(f"Video generation completed. URL: {video_url}")
                break
            elif status == "failed":
                error_msg = response_json.get("error", "Unknown error")
                logging.error(f"Video generation failed: {error_msg}")
                raise ValueError(f"Video generation failed: {error_msg}")
            else:
                logging.info(f"Video generation status: {status}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue

        return video_url

    async def generate_single_video(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        duration: Literal[4, 5, 10] = 5,
        **kwargs,
    ) -> VideoOutput:
        task_id = await self.create_video_generation_task(
            prompt, reference_image_paths, resolution, aspect_ratio, duration
        )
        video_url = await self.query_video_generation_task(task_id)
        return VideoOutput(fmt="url", ext="mp4", data=video_url)
