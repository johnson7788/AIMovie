import base64
import json
import logging
import os
import time
import aiohttp
import asyncio
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional

from PIL import Image

from interfaces.video_output import VideoOutput
from utils.style_prompts import expand_video_style_prompt, is_real_person_rejection


def _extract_output(response_json: Dict[str, Any]) -> str:
    """Extract the primary video URL from a prediction response."""
    video_url, _ = _extract_video_and_last_frame_urls(response_json)
    return video_url


def _looks_like_video_url(value: str) -> bool:
    lower = value.lower().split("?", 1)[0]
    return lower.endswith((".mp4", ".mov", ".webm", ".mkv"))


def _looks_like_image_url(value: str) -> bool:
    lower = value.lower().split("?", 1)[0]
    return lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))


def _extract_video_and_last_frame_urls(response_json: Dict[str, Any]) -> tuple[str, Optional[str]]:
    """Extract video URL and optional last-frame image URL from GPUGEEK response."""
    video_url: Optional[str] = None
    last_frame_url: Optional[str] = None

    output = response_json.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, str):
                continue
            if _looks_like_video_url(item):
                video_url = video_url or item
            elif _looks_like_image_url(item):
                last_frame_url = last_frame_url or item
        if video_url is None and output:
            video_url = output[0]
        if last_frame_url is None and len(output) >= 2 and isinstance(output[1], str):
            if _looks_like_image_url(output[1]):
                last_frame_url = output[1]
    elif isinstance(output, str):
        video_url = output

    for key in ("last_frame", "last_frame_url", "lastFrame", "lastFrameUrl"):
        value = response_json.get(key)
        if isinstance(value, str) and value:
            last_frame_url = value

    nested = response_json.get("output_metadata")
    if isinstance(nested, dict):
        for key in ("last_frame", "last_frame_url", "lastFrame", "lastFrameUrl"):
            value = nested.get(key)
            if isinstance(value, str) and value:
                last_frame_url = value

    if video_url is None:
        raise ValueError(f"Unexpected output format: {output}")
    return video_url, last_frame_url


def _extract_api_error(response_json: Dict[str, Any]) -> str:
    """Collect the most useful failure reason from a GPUGEEK poll response."""
    parts: List[str] = []

    error = response_json.get("error")
    if isinstance(error, dict):
        for key in ("message", "detail", "type", "code"):
            value = error.get(key)
            if value:
                parts.append(str(value))
    elif error:
        parts.append(str(error))

    for key in ("detail", "message", "status_detail", "failure_reason"):
        value = response_json.get(key)
        if value and str(value) not in parts:
            parts.append(str(value))

    logs = response_json.get("logs")
    if isinstance(logs, str) and logs.strip():
        parts.append(logs.strip()[-500:])
    elif isinstance(logs, list):
        for item in logs[-3:]:
            if isinstance(item, dict):
                text = item.get("message") or item.get("msg") or item.get("log")
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))

    if parts:
        return " | ".join(parts)

    return f"Task failed with status: {response_json.get('status', 'failed')}"


def _compress_image_to_b64(image_path: str, max_size: int = 1280, quality: int = 85) -> str:
    """Resize large frame PNGs before upload to reduce upstream failures."""
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    if max(width, height) > max_size:
        ratio = max_size / max(width, height)
        img = img.resize((int(width * ratio), int(height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


class VideoGeneratorDoubaoSeedanceGPUGEEKAPI:
    def __init__(
        self,
        api_key: str = "",
        model: str = "Volcengine/Doubao-Seedance-2.0-fast",
        generate_audio: bool = True,
        return_last_frame: bool = True,
        execution_expires_after: int = 3600,
    ):
        if not api_key:
            api_key = os.environ.get("GPUGEEK", "")
        self.api_key = api_key
        self.base_url = "https://api.gpugeek.com/predictions"
        self.model = model
        self.generate_audio = generate_audio
        self.return_last_frame = return_last_frame
        self.execution_expires_after = execution_expires_after

    async def _create_prediction(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        duration: Literal[4, 5, 10] = 5,
        *,
        generate_audio: Optional[bool] = None,
    ) -> Dict[str, Any]:
        if len(reference_image_paths) > 2:
            raise ValueError("reference_image_paths must contain 0, 1, or 2 images.")

        use_audio = self.generate_audio if generate_audio is None else generate_audio

        logging.info(
            f"Sending video generation request to GPUGEEK {self.model} "
            f"(images={len(reference_image_paths)}, duration={duration}s, "
            f"generate_audio={use_audio})..."
        )

        resolution_map = {"480p": "480p", "720p": "720p", "1080p": "1080p"}
        supported_ratios = {"16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"}
        ratio_value = aspect_ratio if aspect_ratio in supported_ratios else "adaptive"

        input_data: Dict[str, Any] = {
            "task_type": "reference",
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution_map.get(resolution, "720p"),
            "ratio": ratio_value,
            "watermark": False,
            "generate_audio": use_audio,
            "return_last_frame": self.return_last_frame,
            "execution_expires_after": self.execution_expires_after,
        }

        if len(reference_image_paths) >= 1:
            input_data["images"] = [
                _compress_image_to_b64(path) for path in reference_image_paths
            ]

        payload = {
            "model": self.model,
            "input": input_data,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=300)
        while True:
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(self.base_url, headers=headers, json=payload) as response:
                        logging.info(f"Video create request HTTP status: {response.status}")
                        response_json = await response.json()
                        logging.debug(f"Create video prediction response: {response_json}")
                        if response.status >= 400:
                            error_detail = _extract_api_error(response_json)
                            logging.error(
                                f"Video create request failed with HTTP {response.status}: {error_detail}"
                            )
                            raise ValueError(
                                f"Video creation failed (HTTP {response.status}): {error_detail}"
                            )
                        if response_json.get("error"):
                            error_detail = _extract_api_error(response_json)
                            logging.error(f"Video create API error: {error_detail}")
                            raise ValueError(f"Video creation failed: {error_detail}")
                        return response_json
            except asyncio.TimeoutError:
                logging.error("Video create request timed out. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue
            except ValueError:
                raise
            except Exception as e:
                logging.error(f"Error creating video generation task: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue

    async def _poll_prediction(self, prediction_id: str, headers: dict) -> tuple[str, Optional[str]]:
        url = f"{self.base_url}/{prediction_id}"
        max_polls = 600
        start_time = time.time()
        last_log_time = start_time
        log_interval = 30

        timeout = aiohttp.ClientTimeout(total=30)
        for _ in range(max_polls):
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        response_json = await response.json()
                        logging.debug(f"Poll response: {response_json}")
            except asyncio.TimeoutError:
                logging.warning("Poll request timed out. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue
            except Exception as e:
                logging.error(f"Error polling video task: {e}. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                continue

            status = response_json.get("status")
            if status == "succeeded":
                elapsed = time.time() - start_time
                video_url, last_frame_url = _extract_video_and_last_frame_urls(response_json)
                logging.info(
                    f"Video generation completed (elapsed: {elapsed:.0f}s). URL: {video_url}"
                )
                if last_frame_url:
                    logging.info("Seedance returned last-frame URL for continuity handoff.")
                return video_url, last_frame_url
            if status == "failed":
                elapsed = time.time() - start_time
                error_msg = _extract_api_error(response_json)
                logging.error(
                    f"Video generation failed after {elapsed:.0f}s: {error_msg} "
                    f"(task={prediction_id}, response={json.dumps(response_json, ensure_ascii=False)[:800]})"
                )
                raise ValueError(f"Video generation failed: {error_msg}")
            now = time.time()
            elapsed = now - start_time
            if now - last_log_time >= log_interval:
                logging.info(
                    f"Video generation in progress (status={status}, elapsed: {elapsed:.0f}s)..."
                )
                last_log_time = now
            await asyncio.sleep(2)

        raise TimeoutError(f"Video generation timed out after {max_polls} polls")

    async def _generate_once(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"],
        aspect_ratio: str,
        duration: Literal[4, 5, 10],
        *,
        generate_audio: Optional[bool] = None,
    ) -> VideoOutput:
        response_json = await self._create_prediction(
            prompt,
            reference_image_paths,
            resolution,
            aspect_ratio,
            duration,
            generate_audio=generate_audio,
        )

        status = response_json.get("status")
        if status == "succeeded":
            video_url, last_frame_url = _extract_video_and_last_frame_urls(response_json)
            logging.info(f"Video generation completed synchronously. URL: {video_url}")
            return VideoOutput(fmt="url", ext="mp4", data=video_url, last_frame_url=last_frame_url)

        if status == "failed":
            error_msg = _extract_api_error(response_json)
            logging.error(f"Video generation failed: {error_msg}")
            raise ValueError(f"Video generation failed: {error_msg}")

        task_id = response_json["id"]
        logging.info(f"Video generation task created. ID: {task_id}, status: {status}")
        video_url, last_frame_url = await self._poll_prediction(task_id, {
            "Authorization": f"Bearer {self.api_key}",
        })
        return VideoOutput(fmt="url", ext="mp4", data=video_url, last_frame_url=last_frame_url)

    async def generate_single_video(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        duration: Literal[4, 5, 10] = 5,
        *,
        style: str = "",
        **kwargs,
    ) -> VideoOutput:
        style = style or kwargs.get("style", "")
        last_error: Optional[Exception] = None
        reference_rejected_as_real_person = False
        text_only_prompt: Optional[str] = None

        try:
            return await self._generate_once(
                prompt,
                reference_image_paths,
                resolution,
                aspect_ratio,
                duration,
                generate_audio=self.generate_audio,
            )
        except ValueError as exc:
            last_error = exc
            if is_real_person_rejection(str(exc)) and reference_image_paths:
                reference_rejected_as_real_person = True
                if len(reference_image_paths) > 1:
                    logging.warning(
                        "Seedance rejected multi-image references as a real person. "
                        "Retrying with the first-frame reference only..."
                    )
                    try:
                        return await self._generate_once(
                            prompt,
                            reference_image_paths[:1],
                            resolution,
                            aspect_ratio,
                            duration,
                            generate_audio=self.generate_audio,
                        )
                    except ValueError as first_ref_exc:
                        last_error = first_ref_exc
                        if not is_real_person_rejection(str(first_ref_exc)):
                            raise

                logging.warning(
                    "Seedance rejected reference image as a real person. "
                    "Retrying text-only video generation and disabling reference-image retries..."
                )
                video_style = expand_video_style_prompt(style)
                text_only_prompt = f"{prompt}\n\nVisual style: {video_style}"
                try:
                    return await self._generate_once(
                        text_only_prompt,
                        [],
                        resolution,
                        aspect_ratio,
                        duration,
                        generate_audio=self.generate_audio,
                    )
                except ValueError as retry_exc:
                    last_error = retry_exc

        if self.generate_audio and last_error is not None:
            retry_refs = [] if reference_rejected_as_real_person else reference_image_paths
            retry_prompt = text_only_prompt or prompt
            logging.warning(
                "Retrying Seedance video generation with dialogue audio enabled "
                "(images=%d)...",
                len(retry_refs),
            )
            await asyncio.sleep(3)
            try:
                return await self._generate_once(
                    retry_prompt,
                    retry_refs,
                    resolution,
                    aspect_ratio,
                    duration,
                    generate_audio=True,
                )
            except ValueError as exc:
                last_error = exc

        if last_error:
            raise last_error
        raise RuntimeError("Video generation failed without a captured error")
