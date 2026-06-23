"""Agnes AI Video Generator — async task-based API.

Create task: POST https://apihub.agnes-ai.com/v1/videos
Poll result: GET  https://apihub.agnes-ai.com/agnesapi?video_id=<VIDEO_ID>
Model:       agnes-video-v2.0
Docs:        https://www.agnes-ai.com/doc/agnes-video-v20
"""

import logging
import os
import time
import asyncio
import json
from typing import List, Literal, Optional

import aiohttp

from interfaces.video_output import VideoOutput
from utils.rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Resolution / aspect-ratio helpers
# ---------------------------------------------------------------------------

# (width, height) tuples keyed by (resolution, aspect_ratio)
_WH_TABLE = {
    # 16:9
    ("480p", "16:9"):  (854, 480),
    ("720p", "16:9"):  (1280, 720),
    ("1080p", "16:9"): (1152, 768),  # Agnes default for 16:9
    # 9:16
    ("480p", "9:16"):  (480, 854),
    ("720p", "9:16"):  (720, 1280),
    ("1080p", "9:16"): (768, 1152),
    # 1:1
    ("480p", "1:1"):   (480, 480),
    ("720p", "1:1"):   (720, 720),
    ("1080p", "1:1"):  (768, 768),
    # 4:3
    ("720p", "4:3"):   (960, 720),
    ("1080p", "4:3"):  (1024, 768),
    # 3:4
    ("720p", "3:4"):   (720, 960),
    ("1080p", "3:4"):  (768, 1024),
}
_DEFAULT_WH = (1152, 768)


def _resolve_wh(resolution: str, aspect_ratio: str) -> tuple[int, int]:
    return _WH_TABLE.get(
        (resolution, aspect_ratio),
        _WH_TABLE.get((resolution, "16:9"), _DEFAULT_WH),
    )


# ---------------------------------------------------------------------------
# Duration helpers — num_frames must satisfy 8n+1 and <= 441
# ---------------------------------------------------------------------------

# (duration_seconds) -> (num_frames, frame_rate)
# formula: seconds = num_frames / frame_rate, num_frames = 8n+1
_DURATION_MAP = {
    3:  (73,  24),   # ~3.0s
    4:  (97,  24),   # ~4.0s
    5:  (121, 24),   # ~5.0s
    6:  (145, 24),   # ~6.0s
    7:  (169, 24),   # ~7.0s
    8:  (193, 24),   # ~8.0s
    9:  (217, 24),   # ~9.0s
    10: (241, 24),   # ~10.0s
    12: (289, 24),   # ~12.0s
    15: (361, 24),   # ~15.0s
    18: (433, 24),   # ~18.0s
}


def _resolve_frames(duration: int) -> tuple[int, int]:
    """Return (num_frames, frame_rate) for a given duration in seconds."""
    if duration in _DURATION_MAP:
        return _DURATION_MAP[duration]
    # Find the closest entry <= duration
    best = max(k for k in _DURATION_MAP if k <= max(duration, 3))
    return _DURATION_MAP[best]


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class VideoGeneratorAgnesAPI:
    """Generates videos via the Agnes AI async task-based Video API."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "agnes-video-v2.0",
        base_url: str = "https://apihub.agnes-ai.com",
        poll_interval: int = 5,
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
        self.poll_interval = poll_interval
        self.rate_limiter = rate_limiter

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate_single_video(
        self,
        prompt: str,
        reference_image_paths: List[str],
        resolution: Literal["480p", "720p", "1080p"] = "720p",
        aspect_ratio: str = "16:9",
        duration: int = 5,
        **kwargs,
    ) -> VideoOutput:
        logging.info(
            "Sending video generation request to Agnes %s "
            "(images=%d, duration=%ds, resolution=%s, aspect=%s)...",
            self.model, len(reference_image_paths), duration, resolution, aspect_ratio,
        )

        if self.rate_limiter:
            await self.rate_limiter.acquire()

        num_frames, frame_rate = _resolve_frames(duration)
        width, height = _resolve_wh(resolution, aspect_ratio)

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "num_frames": num_frames,
            "frame_rate": frame_rate,
            "width": width,
            "height": height,
        }

        # Attach reference images
        if len(reference_image_paths) == 1:
            # Single image: use top-level `image` field (URL or data URI)
            payload["image"] = _path_to_data_uri(reference_image_paths[0])
        elif len(reference_image_paths) >= 2:
            # Multi-image: use extra_body for keyframes
            payload["extra_body"] = {
                "image": [_path_to_data_uri(p) for p in reference_image_paths],
                "mode": "keyframes",
            }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        create_url = f"{self.base_url}/v1/videos"
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(create_url, json=payload, headers=headers) as resp:
                logging.info("Agnes video create HTTP status: %d", resp.status)
                response_json = await resp.json()

                if resp.status >= 400:
                    error_detail = (
                        response_json.get("error", {}).get("message")
                        if isinstance(response_json.get("error"), dict)
                        else response_json.get("error") or str(response_json)
                    )
                    raise ValueError(
                        f"Agnes video creation failed (HTTP {resp.status}): {error_detail}"
                    )

        video_id = response_json.get("video_id") or response_json.get("id", "")
        task_id = response_json.get("task_id") or response_json.get("id", "")
        status = response_json.get("status", "queued")
        logging.info(
            "Agnes video task created: video_id=%s, task_id=%s, status=%s",
            video_id, task_id, status,
        )

        # Poll until completed
        video_url = await self._poll_result(video_id, task_id, headers)
        return VideoOutput(fmt="url", ext="mp4", data=video_url)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _poll_result(
        self, video_id: str, task_id: str, headers: dict
    ) -> str:
        """Poll the Agnes video API until the task completes or times out."""
        # Prefer the recommended query endpoint using video_id
        if video_id:
            poll_url = f"{self.base_url}/agnesapi?video_id={video_id}"
        else:
            poll_url = f"{self.base_url}/v1/videos/{task_id}"

        max_polls = 360   # ~30 min at 5s interval
        start_time = time.time()
        last_log_time = start_time
        LOG_INTERVAL = 30

        timeout = aiohttp.ClientTimeout(total=30)
        for _ in range(max_polls):
            await asyncio.sleep(self.poll_interval)
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(poll_url, headers=headers) as resp:
                        response_json = await resp.json()
            except asyncio.TimeoutError:
                logging.warning("Agnes video poll timed out, retrying...")
                continue
            except Exception as e:
                logging.error("Agnes video poll error: %s, retrying...", e)
                continue

            status = response_json.get("status", "")
            progress = response_json.get("progress", 0)

            if status == "completed":
                elapsed = time.time() - start_time
                video_url = response_json.get("remixed_from_video_id") or ""
                if not video_url:
                    raise ValueError(
                        f"Agnes video completed but no URL found. Response: {response_json}"
                    )
                logging.info(
                    "Agnes video generation completed (elapsed: %.0fs). URL: %s",
                    elapsed, video_url[:120],
                )
                return video_url

            if status == "failed":
                elapsed = time.time() - start_time
                error = response_json.get("error") or "Unknown error"
                logging.error(
                    "Agnes video generation failed after %.0fs: %s",
                    elapsed, error,
                )
                raise ValueError(f"Agnes video generation failed: {error}")

            # Log progress periodically
            now = time.time()
            if now - last_log_time >= LOG_INTERVAL:
                logging.info(
                    "Agnes video generation in progress (status=%s, progress=%s%%, elapsed: %.0fs)...",
                    status, progress, now - start_time,
                )
                last_log_time = now

        raise TimeoutError(
            f"Agnes video generation timed out after {max_polls} polls"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _path_to_data_uri(path: str) -> str:
    """Convert a local file to a data URI for the Agnes API."""
    from utils.image import image_path_to_b64
    return image_path_to_b64(path, mime=True)
