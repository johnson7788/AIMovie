"""Filter and normalize SSE progress events to keep the frontend responsive."""

from __future__ import annotations

from typing import Optional

NOISY_LOGGER_PREFIXES = (
    "httpx",
    "httpcore",
    "urllib3",
    "openai",
    "langchain",
    "langchain_core",
    "langchain_community",
    "asyncio",
    "PIL",
    "multipart",
    "watchfiles",
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
    "charset_normalizer",
    "requests",
)

IMPORTANT_LOG_LEVELS = frozenset({"WARNING", "ERROR", "CRITICAL"})


def should_forward_log(record_name: str, level_name: str, message: str) -> bool:
    """Return True when a log record should be streamed to the client."""
    if level_name in IMPORTANT_LOG_LEVELS:
        return True
    if level_name != "INFO":
        return False

    for prefix in NOISY_LOGGER_PREFIXES:
        if record_name == prefix or record_name.startswith(f"{prefix}."):
            return False

    lower = message.lower()
    if "poll" in lower and "video" in lower:
        return False
    if "probed " in lower and ".mp4" in lower:
        return False
    if "running ffmpeg:" in lower:
        return False
    return True


def sanitize_progress_event(event: dict) -> Optional[dict]:
    """Return a client-safe event, or None to drop it."""
    event_type = event.get("type")

    if event_type == "log":
        message = event.get("message", "")
        if len(message) > 400:
            return {**event, "message": message[:400] + "…"}
        return event

    if event_type == "artifact":
        return _sanitize_artifact(event)

    return event


def _sanitize_artifact(event: dict) -> Optional[dict]:
    stage = event.get("stage") or ""
    file_type = event.get("file_type")

    if file_type in ("text", "json"):
        preview = event.get("content_preview")
        if preview and len(preview) > 800:
            return {**event, "content_preview": preview[:800] + "…"}
        return event

    if file_type == "video":
        path = event.get("file_path") or ""
        if (
            path.endswith("final_video.mp4")
            or stage.startswith("scene_")
            or stage == "concatenate"
        ):
            return event
        if stage == "videos":
            shot_idx = event.get("shot_idx")
            return {
                "type": "progress",
                "stage": "frames",
                "message": f"镜头 {shot_idx} 视频已生成" if shot_idx is not None else "镜头视频已生成",
                "shot_idx": shot_idx,
            }
        return event

    if file_type == "image":
        if stage == "character_portraits":
            return event
        if stage == "scene_anchor":
            return event
        if stage == "frames":
            shot_idx = event.get("shot_idx")
            frame_type = event.get("frame_type") or "frame"
            if shot_idx is not None:
                message = f"镜头 {shot_idx} {frame_type} 已生成"
            else:
                message = f"{frame_type} 已生成"
            return {
                "type": "progress",
                "stage": "frames",
                "message": message,
                "shot_idx": shot_idx,
                "frame_type": frame_type,
            }

    return event
