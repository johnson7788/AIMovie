import logging
import os
from typing import List, Literal, Optional
import asyncio
import aiohttp
from interfaces.video_output import VideoOutput
from utils.image import image_path_to_b64
from utils.rate_limiter import RateLimiter


class VideoGeneratorDoubaoSeedanceVolcengineAPI:
    def __init__(
        self,
        api_key: str = "",
        t2v_model: str = "doubao-seedance-2-0-fast-260128",
        ff2v_model: str = "doubao-seedance-2-0-fast-260128",
        flf2v_model: str = "doubao-seedance-2-0-fast-260128",
        rate_limiter: Optional[RateLimiter] = None,
        max_iterations: int = 200,
        max_retries: int = 2,
    ):
        if not api_key:
            api_key = os.environ.get("ARK_API_KEY", "")
        self.api_key = api_key
        self.t2v_model = t2v_model
        self.ff2v_model = ff2v_model
        self.flf2v_model = flf2v_model
        self.rate_limiter = rate_limiter
        self.max_iterations = max_iterations
        self.max_retries = max_retries

    async def create_video_generation_task(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        fps: Literal[16, 24] = 16,
        duration: Literal[5, 10] = 5,
    ) -> str:
        if len(reference_image_paths) == 0:
            model = self.t2v_model
        elif len(reference_image_paths) == 1:
            model = self.ff2v_model
        elif len(reference_image_paths) == 2:
            model = self.flf2v_model
        else:
            raise ValueError("reference_image_paths must contain 1 or 2 images.")

        logging.info(f"Calling {model} to generate video...")

        if self.rate_limiter:
            await self.rate_limiter.acquire()

        url = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"

        content = [
            {
                "type": "text",
                "text": prompt + f"  --resolution {resolution}  --duration {duration} --camerafixed false --watermark true"
            }
        ]
        if len(reference_image_paths) >= 1:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_path_to_b64(reference_image_paths[0])
                    },
                    "role": "first_frame",
                }
            )
        if len(reference_image_paths) >= 2:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_path_to_b64(reference_image_paths[1])
                    },
                    "role": "last_frame",
                }
            )

        payload = {
            "model": model,
            "content": content
        }

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=120)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logging.info(f"Sending video task creation request to {model} (attempt {attempt}/{max_retries}, timeout=120s)...")
                    async with session.post(url, headers=headers, json=payload) as response:
                        logging.info(f"Video task creation HTTP status: {response.status}")
                        response_json = await response.json()
                        logging.debug(f"Create task response: {response_json}")
                        if "error" in response_json:
                            logging.error(f"Video task creation API error: {response_json['error']}")
                            raise ValueError(f"Video task creation failed: {response_json['error']}")
                        task_id = response_json["id"]
            except ValueError:
                raise
            except (aiohttp.ClientTimeout, TimeoutError):
                logging.error(f"Video task creation timed out (attempt {attempt}/{max_retries})")
                if attempt == max_retries:
                    raise TimeoutError(f"Video task creation timed out after {max_retries} attempts")
                await asyncio.sleep(1)
                continue
            except Exception as e:
                logging.error(f"Error occurred while creating video generation task (attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    raise
                await asyncio.sleep(1)
                continue
            break
        else:
            raise RuntimeError(f"Video task creation failed after {max_retries} attempts")

        logging.info(f"Video generation task created successfully. Task ID: {task_id}")
        return task_id

    async def query_video_generation_task(
        self,
        task_id: str,
    ) -> str:
        url = f"https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        max_iterations = self.max_iterations
        for iteration in range(1, max_iterations + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    logging.info(f"Querying video task {task_id} (iteration {iteration}/{max_iterations}, timeout=30s)...")
                    async with session.get(url, headers=headers) as response:
                        logging.info(f"Video task query HTTP status: {response.status}")
                        response_json = await response.json()

            except aiohttp.ClientTimeout:
                logging.warning(f"Video task query timed out (iteration {iteration}/{max_iterations})")
                if iteration == max_iterations:
                    raise TimeoutError(f"Video task query timed out after {max_iterations} iterations")
                await asyncio.sleep(2)
                continue
            except Exception as e:
                logging.error(f"Error occurred while querying video generation task: {e}. Retrying in 2 seconds...")
                if iteration == max_iterations:
                    raise
                await asyncio.sleep(2)
                continue

            status = response_json["status"]
            if status == "succeeded":
                video_url = response_json["content"]["video_url"]
                logging.info(f"Video generation completed successfully. Video URL: {video_url}")
                break
            elif status == "failed":
                logging.error(f"Video generation failed. Response: {response_json}")
                raise ValueError("Video generation failed.")
            else:
                logging.info(f"Video generation is still in progress (status={status}). Checking again in 2 seconds...")
                await asyncio.sleep(2)
                continue
        else:
            raise TimeoutError(f"Video task {task_id} did not complete after {max_iterations} iterations (~{max_iterations * 2}s)")

        return video_url

    async def generate_single_video(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        fps: Literal[16, 24] = 16,
        duration: Literal[5, 10] = 5,
    ) -> VideoOutput:
        task_id = await self.create_video_generation_task(prompt, reference_image_paths, resolution, aspect_ratio, fps, duration)
        for retry in range(self.max_retries + 1):
            try:
                video_url = await self.query_video_generation_task(task_id)
                break
            except TimeoutError:
                if retry < self.max_retries:
                    logging.warning(
                        f"Video task {task_id} timed out, retrying query "
                        f"({retry + 1}/{self.max_retries})..."
                    )
                else:
                    raise TimeoutError(
                        f"Video task {task_id} did not complete after "
                        f"{self.max_retries + 1} query attempts "
                        f"({(self.max_retries + 1) * self.max_iterations * 2}s total)"
                    )
        return VideoOutput(fmt="url", ext="mp4", data=video_url)
