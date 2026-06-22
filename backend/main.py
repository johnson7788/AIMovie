import os
import logging
import logging.handlers
import sys

from dotenv import load_dotenv
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Load .env from the backend directory (next to this file) — must happen before reading LOG_LEVEL
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
SERVER_PORT = int(os.getenv("SERVER_PORT", "8666"))

# ── Logging setup ──────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
LOG_DIR = os.path.join(_BACKEND_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Detailed format for file logs; shorter format for console
FILE_FORMAT = logging.Formatter(
    "%(asctime)s.%(msecs)03d [%(name)s] %(levelname)s %(pathname)s:%(lineno)d: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
CONSOLE_FORMAT = logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Root logger — capture everything at LOG_LEVEL
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

# Remove any pre-existing handlers (e.g. from basicConfig in submodules)
root_logger.handlers.clear()

# Console handler — stderr so it won't interfere with stdout piping
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
console_handler.setFormatter(CONSOLE_FORMAT)
root_logger.addHandler(console_handler)

# File handler — rotating, 10 MB per file, keep 5 backups
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(LOG_DIR, "backend.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)  # File always captures DEBUG
file_handler.setFormatter(FILE_FORMAT)
root_logger.addHandler(file_handler)

# Ensure uvicorn loggers are also at LOG_LEVEL
for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
    uv_logger = logging.getLogger(name)
    uv_logger.handlers.clear()
    uv_logger.propagate = True  # let root handle it

logging.getLogger("uvicorn.access").setLevel(logging.INFO)  # access log stays at INFO (too noisy at DEBUG)

_log = logging.getLogger(__name__)
_log.info(f"Logging initialized — level={LOG_LEVEL}, file={os.path.join(LOG_DIR, 'backend.log')}")

# Ensure UTF-8 text handling on Windows (avoid GBK decode errors).
if os.name == "nt":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        import sys
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import asyncio
import hashlib
import json as json_module
import re
import sqlite3
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import aiohttp
import yaml
from fastapi import FastAPI, HTTPException, Query, Header, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, Response
from pydantic import BaseModel, Field
from progress_manager import ProgressManager
import auth as auth_service
import user_works as user_works_service
import actors as actors_service
import actor_image
from utils.retry import format_exception

def _import_pipelines():
    """Lazy import pipelines to avoid import errors when deps are missing."""
    from pipelines.script2video_pipeline import Script2VideoPipeline
    from pipelines.idea2video_pipeline import Idea2VideoPipeline
    return Script2VideoPipeline, Idea2VideoPipeline


def _get_image_generator(model_id: Optional[str] = None, config_path: str = "configs/script2video.yaml"):
    """Create an image generator from config.

    model_id maps to a generator class:
      - "nanobanana" / "google" / "1" -> ImageGeneratorNanobananaGoogleAPI
      - "seedream" / "volcengine" / "2" -> ImageGeneratorDoubaoSeedreamVolcengineAPI
      - "hunyuan" / "tencent" / "3" -> ImageGeneratorHunyuanTencentAPI
      - "gpugeek" / "4" -> ImageGeneratorDoubaoSeedreamGPUGEEKAPI
      - None -> use config default
    """
    from tools.render_backend import RenderBackend

    with open(_backend_path(config_path), encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Override image generator class based on model_id
    if model_id in ("1", "nanobanana", "google", "gemini"):
        config["image_generator"]["class_path"] = "tools.ImageGeneratorNanobananaGoogleAPI"
    elif model_id in ("2", "seedream", "volcengine", "doubao"):
        config["image_generator"]["class_path"] = "tools.ImageGeneratorDoubaoSeedreamVolcengineAPI"
    elif model_id in ("3", "hunyuan", "tencent"):
        config["image_generator"]["class_path"] = "tools.ImageGeneratorHunyuanTencentAPI"
    elif model_id in ("4", "gpugeek"):
        config["image_generator"]["class_path"] = "tools.ImageGeneratorDoubaoSeedreamGPUGEEKAPI"

    backend = RenderBackend.from_config(config)
    return backend.image_generator


async def _download_image(url: str) -> str:
    """Download image from URL to a temp file. Returns file path."""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Only http(s) image URLs are supported")
    ext = ".png"
    if "." in url.split("/")[-1]:
        ext = "." + url.split("/")[-1].split(".")[-1].split("?")[0]
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            ext = ".png"
    fd, path = tempfile.mkstemp(suffix=ext)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to download image: HTTP {resp.status}",
                )
            data = await resp.read()
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def _backend_path(*parts: str) -> str:
    return os.path.join(_BACKEND_DIR, *parts)


def _default_pipeline_config(basename: str) -> str:
    """Prefer provider-specific config when credentials are available."""
    if os.environ.get("GPUGEEK"):
        gpugeek_path = f"configs/{basename}_gpugeek.yaml"
        if os.path.exists(_backend_path(gpugeek_path)):
            return gpugeek_path
    return f"configs/{basename}.yaml"


def _track_background_task(coro):
    """Run a background coroutine and log unhandled exceptions."""
    task = asyncio.create_task(coro)

    def _done(t: asyncio.Task):
        try:
            t.result()
        except Exception:
            logging.exception("Background task failed")

    task.add_done_callback(_done)
    return task

app = FastAPI(
    title="VixP3D API",
    description="Agentic Video Generation API - supports script2video and idea2video modes",
    version="0.1.0",
)

# --- Request logging middleware ---
MAX_LOG_BODY = 2000  # truncate logged bodies to this many chars

async def _read_request_body(request) -> str:
    """Read and return request body as text, truncated."""
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return ""
        body_str = body_bytes.decode("utf-8", errors="replace")
        if len(body_str) > MAX_LOG_BODY:
            body_str = body_str[:MAX_LOG_BODY] + f"... <truncated, total {len(body_str)} chars>"
        return body_str
    except Exception:
        return "<unable to read body>"

@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()

    # Log request
    req_body = await _read_request_body(request)
    if req_body:
        _log.info(f"--> {request.method} {request.url.path}  body={req_body}")
    else:
        qs = str(request.query_params)
        if qs:
            _log.info(f"--> {request.method} {request.url.path}  params={qs}")
        else:
            _log.info(f"--> {request.method} {request.url.path}")

    response = await call_next(request)
    elapsed_ms = (time.time() - start_time) * 1000

    # Log response — but NOT for streams / files (they would be consumed)
    resp_body = ""
    content_type = response.headers.get("content-type", "")
    is_stream = (
        "text/event-stream" in content_type
        or isinstance(response, StreamingResponse)
        or isinstance(response, FileResponse)
    )

    if not is_stream:
        try:
            # Consume the response body, log it, then rebuild it
            body_chunks = []
            async for chunk in response.body_iterator:
                body_chunks.append(chunk)
            resp_bytes = b"".join(body_chunks)
            resp_body = resp_bytes.decode("utf-8", errors="replace")
            if len(resp_body) > MAX_LOG_BODY:
                resp_body = resp_body[:MAX_LOG_BODY] + f"... <truncated, total {len(resp_body)} chars>"

            # Rebuild the response with the same body
            response = Response(
                content=resp_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=getattr(response, "background", None),
            )
        except Exception:
            resp_body = "<unable to read response body>"

    status = response.status_code
    log_msg = f"<-- {request.method} {request.url.path}  {status}  {elapsed_ms:.0f}ms"
    if resp_body:
        log_msg += f"  resp={resp_body}"

    if status >= 500:
        _log.error(log_msg)
    elif status >= 400:
        _log.warning(log_msg)
    else:
        _log.info(log_msg)

    return response

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SQLite database ---
DB_PATH = _backend_path("tasks.db")

# --- Uploaded / generated media storage ---
UPLOADS_DIR = _backend_path(".uploads")
_SAFE_DIR_RE = re.compile(r"^[A-Za-z0-9_\-/]+$")
_ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            error TEXT,
            working_dir TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add working_dir column if it doesn't exist (migration for existing DBs)
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN working_dir TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    auth_service.init_auth_tables(conn)
    user_works_service.init_works_tables(conn)
    actors_service.init_actor_tables(conn)
    conn.commit()
    return conn


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# --- Response envelope helpers ---
def success_response(data):
    return {"code": 200, "data": data, "msg": "success"}


def error_response(code: int, msg: str):
    return {"code": code, "data": None, "msg": msg}


# --- Log handler that forwards to ProgressManager ---
class TaskLogHandler(logging.Handler):
    """Forwards filtered log records to ProgressManager as 'log' events."""

    def __init__(self, task_id: str):
        super().__init__(level=logging.INFO)
        self.task_id = task_id

    def emit(self, record):
        try:
            from utils.progress_events import should_forward_log

            msg = record.getMessage()
            if not should_forward_log(record.name, record.levelname, msg):
                return
            pm = ProgressManager.get_instance()
            pm.emit(self.task_id, {
                "type": "log",
                "level": record.levelname,
                "message": self.format(record),
            })
        except Exception:
            self.handleError(record)


def _install_log_handler(task_id: str) -> TaskLogHandler:
    """Install a log handler that forwards to ProgressManager for the given task."""
    handler = TaskLogHandler(task_id)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    # Attach to root logger to capture all logging output
    logging.getLogger().addHandler(handler)
    return handler


def _remove_log_handler(handler: TaskLogHandler):
    """Remove a previously installed log handler."""
    logging.getLogger().removeHandler(handler)


# --- Request models ---
class Script2VideoRequest(BaseModel):
    script: str
    user_requirement: str = ""
    style: str = "Cinematic"
    config_path: str = "configs/script2video.yaml"
    model_id: str = ""
    aspect_ratio: str = ""
    resolution: str = "480p"
    episode_duration: int = 0


class Idea2VideoRequest(BaseModel):
    idea: str
    user_requirement: str = ""
    style: str = "Cinematic"
    config_path: str = "configs/idea2video.yaml"
    model_id: str = ""
    episode_count: int = 0  # 0 = let LLM decide; >0 = force this many episodes
    episode_duration: int = 0  # seconds per episode; 0 = no hard limit
    aspect_ratio: str = ""
    resolution: str = "480p"


class TaskResponse(BaseModel):
    task_id: str
    mode: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


# --- Background runners ---
async def run_script2video(task_id: str, req: Script2VideoRequest):
    Script2VideoPipeline, _ = _import_pipelines()
    pm = ProgressManager.get_instance()
    log_handler = _install_log_handler(task_id)
    try:
        # Resolve provider overrides from model_id BEFORE pipeline init
        chat_override = None
        image_override = None
        video_override = None
        if req.model_id:
            model_info = _find_model_by_id(req.model_id, "creative_script")
            if model_info:
                provider = model_info["provider"]
                model_name = model_info["model"]
                chat_override = _build_provider_chat_model(provider, model_name)
                image_override = _build_provider_image_generator(provider)
                video_override = _build_provider_video_generator(provider)

        pipeline = Script2VideoPipeline.init_from_config(
            config_path=req.config_path,
            chat_model_override=chat_override,
            image_generator_override=image_override,
            video_generator_override=video_override,
        )
        # Use a deterministic cache key so identical inputs reuse the same cache directory.
        cache_key_raw = "|".join([
            req.script,
            req.user_requirement or "",
            req.style,
            req.config_path,
            req.model_id,
            req.aspect_ratio or "",
            req.resolution or "1080p",
            str(req.episode_duration or 0),
        ])
        cache_key = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()[:16]
        pipeline.working_dir = os.path.join(pipeline.working_dir, cache_key)
        os.makedirs(pipeline.working_dir, exist_ok=True)

        # Store working_dir for file serving and update task
        pm.set_working_dir(task_id, pipeline.working_dir)
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET working_dir = ? WHERE task_id = ?",
                (pipeline.working_dir, task_id),
            )

        async def progress_callback(event):
            event["task_id"] = task_id
            # Build file URL for artifact events
            if event.get("type") == "artifact" and event.get("file_path"):
                event["url"] = f"/api/tasks/{task_id}/files/{event['file_path']}"
            pm.emit(task_id, event)

        result_path = await pipeline(
            script=req.script,
            user_requirement=req.user_requirement,
            style=req.style,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
            episode_duration=req.episode_duration,
            progress_callback=progress_callback,
        )
        pm.emit(task_id, {"type": "complete", "result": result_path})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", result_path, task_id),
            )
        _persist_user_work(task_id)
    except Exception as e:
        pm.emit(task_id, {"type": "error", "error": format_exception(e)})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", format_exception(e), task_id),
            )
    finally:
        _remove_log_handler(log_handler)


def _find_model_by_id(model_id: str, scene: Optional[str] = None) -> dict | None:
    """Find a model entry in MODELS_DATA by id, optionally scoped to a scene group."""
    if not model_id:
        return None
    if scene and scene in MODELS_DATA:
        for m in MODELS_DATA[scene]:
            if m.get("id") == model_id:
                return m
    for scene_models in MODELS_DATA.values():
        for m in scene_models:
            if m.get("id") == model_id:
                return m
    return None


def _build_provider_chat_model(provider: str, model_name: str):
    """Build a LangChain chat model for the given provider and model."""
    from utils.provider_presets import resolve_chat_model_config
    from langchain.chat_models import init_chat_model
    import logging
    logger = logging.getLogger(__name__)
    args = resolve_chat_model_config({
        "model": model_name,
        "model_provider": provider,
    })
    # Set a generous timeout so the LLM call doesn't hang forever
    args.setdefault("timeout", 600)
    # Log the effective config (mask API key)
    log_args = dict(args)
    if "api_key" in log_args and log_args["api_key"]:
        key = log_args["api_key"]
        log_args["api_key"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    logger.info(f"Building chat model with args: {log_args}")
    chat_model = init_chat_model(**args)
    logger.info(f"Chat model created: {chat_model.model_name}, base_url={getattr(chat_model, 'openai_api_base', 'N/A')}")
    return chat_model


def _build_provider_image_generator(provider: str):
    """Build an image generator for the given provider."""
    if provider == "tencent":
        from tools.image_generator_hunyuan_tencent_api import ImageGeneratorHunyuanTencentAPI
        return ImageGeneratorHunyuanTencentAPI()
    elif provider == "google":
        from tools.image_generator_nanobanana_google_api import ImageGeneratorNanobananaGoogleAPI
        return ImageGeneratorNanobananaGoogleAPI(api_key=os.environ.get("GOOGLE_API_KEY", ""))
    elif provider == "gpugeek":
        from tools.image_generator_doubao_seedream_gpugeek_api import ImageGeneratorDoubaoSeedreamGPUGEEKAPI
        return ImageGeneratorDoubaoSeedreamGPUGEEKAPI()
    else:
        from tools.image_generator_doubao_seedream_volcengine_api import ImageGeneratorDoubaoSeedreamVolcengineAPI
        return ImageGeneratorDoubaoSeedreamVolcengineAPI()


def _get_video_generator(model_id: Optional[str] = None, config_path: str = "configs/script2video.yaml"):
    """Create a video generator from config, with optional model_id override."""
    from tools.render_backend import RenderBackend

    config_file = _backend_path(config_path)
    with open(config_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    model_info = _find_model_by_id(model_id, "storyboard_video") if model_id else None
    if model_info:
        provider = model_info.get("provider", "")
        if provider == "google":
            config["video_generator"]["class_path"] = "tools.VideoGeneratorVeoGoogleAPI"
        elif provider == "gpugeek":
            config["video_generator"]["class_path"] = "tools.VideoGeneratorDoubaoSeedanceGPUGEEKAPI"
        else:
            config["video_generator"]["class_path"] = "tools.VideoGeneratorDoubaoSeedanceVolcengineAPI"

    backend = RenderBackend.from_config(config)
    return backend.video_generator


def _build_provider_video_generator(provider: str):
    """Build a video generator for the given provider, or fall back to volcengine."""
    if provider == "google":
        from tools.video_generator_veo_google_api import VideoGeneratorVeoGoogleAPI
        return VideoGeneratorVeoGoogleAPI(api_key=os.environ.get("GOOGLE_API_KEY", ""))
    elif provider == "gpugeek":
        from tools.video_generator_doubao_seedance_gpugeek_api import VideoGeneratorDoubaoSeedanceGPUGEEKAPI
        return VideoGeneratorDoubaoSeedanceGPUGEEKAPI(generate_audio=True)
    else:
        from tools.video_generator_doubao_seedance_volcengine_api import VideoGeneratorDoubaoSeedanceVolcengineAPI
        return VideoGeneratorDoubaoSeedanceVolcengineAPI()


async def run_idea2video(task_id: str, req: Idea2VideoRequest):
    _, Idea2VideoPipeline = _import_pipelines()
    pm = ProgressManager.get_instance()
    log_handler = _install_log_handler(task_id)
    try:
        # Resolve provider overrides from model_id BEFORE pipeline init
        chat_override = None
        image_override = None
        video_override = None
        if req.model_id:
            model_info = _find_model_by_id(req.model_id, "creative_script")
            if model_info:
                provider = model_info["provider"]
                model_name = model_info["model"]
                chat_override = _build_provider_chat_model(provider, model_name)
                image_override = _build_provider_image_generator(provider)
                video_override = _build_provider_video_generator(provider)

        pipeline = Idea2VideoPipeline.init_from_config(
            config_path=req.config_path,
            chat_model_override=chat_override,
            image_generator_override=image_override,
            video_generator_override=video_override,
        )
        # Use a deterministic cache key from input parameters so identical
        # inputs reuse the same cache directory and skip recomputation.
        cache_key_raw = "|".join([
            req.idea,
            req.user_requirement or "",
            req.style,
            str(req.episode_count),
            str(req.episode_duration),
            req.model_id,
            req.config_path,
            req.aspect_ratio or "",
            req.resolution or "1080p",
        ])
        cache_key = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()[:16]
        pipeline.working_dir = os.path.join(pipeline.working_dir, cache_key)
        os.makedirs(pipeline.working_dir, exist_ok=True)

        # Store working_dir for file serving and update task
        pm.set_working_dir(task_id, pipeline.working_dir)
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET working_dir = ? WHERE task_id = ?",
                (pipeline.working_dir, task_id),
            )

        async def progress_callback(event):
            event["task_id"] = task_id
            if event.get("type") == "artifact" and event.get("file_path"):
                event["url"] = f"/api/tasks/{task_id}/files/{event['file_path']}"
            pm.emit(task_id, event)

        result_path = await pipeline(
            idea=req.idea,
            user_requirement=req.user_requirement,
            style=req.style,
            episode_count=req.episode_count,
            episode_duration=req.episode_duration,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
            progress_callback=progress_callback,
        )
        pm.emit(task_id, {"type": "complete", "result": result_path})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", result_path, task_id),
            )
        _persist_user_work(task_id)
    except Exception as e:
        pm.emit(task_id, {"type": "error", "error": format_exception(e)})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", format_exception(e), task_id),
            )
    finally:
        _remove_log_handler(log_handler)


# --- Helper to generate simple colored SVG data URIs for placeholders ---
def _style_img(color1, color2):
    """Generate a gradient SVG data URI for style preview placeholders."""
    import urllib.parse
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
        <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:{color1}"/><stop offset="100%" style="stop-color:{color2}"/>
        </linearGradient></defs><rect width="400" height="300" fill="url(#g)"/>
        </svg>'''
    compact = ' '.join(svg.split())
    return f"data:image/svg+xml,{urllib.parse.quote(compact, safe='')}"


def _model_icon(color1: str, color2: str, label: str) -> str:
    """Generate a small gradient SVG icon for model list / avatar."""
    import urllib.parse
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
        f'<defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{color1}"/><stop offset="100%" stop-color="{color2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="64" height="64" rx="14" fill="url(#g)"/>'
        f'<text x="32" y="40" text-anchor="middle" fill="#fff" font-size="15" '
        f'font-family="system-ui,Arial,sans-serif" font-weight="700">{label}</text>'
        f'</svg>'
    )
    return f"data:image/svg+xml,{urllib.parse.quote(svg, safe='')}"


_MODEL_ICONS = {
    "volcengine": _model_icon("#0066FF", "#FF6B35", "豆"),
    "tencent": _model_icon("#00B96B", "#0084FF", "混"),
    "google": _model_icon("#4285F4", "#EA4335", "G"),
    "openai": _model_icon("#10A37F", "#074763", "AI"),
    "gpugeek": _model_icon("#6366F1", "#8B5CF6", "DS"),
}


def _with_model_icon(entry: dict) -> dict:
    item = dict(entry)
    if not item.get("icon"):
        item["icon"] = _MODEL_ICONS.get(
            item.get("provider", ""),
            _model_icon("#64748B", "#334155", "M"),
        )
    return item


def _enrich_models_data(data: dict) -> dict:
    return {scene: [_with_model_icon(m) for m in models] for scene, models in data.items()}


# --- Static data for frontend ---
MODELS_DATA = _enrich_models_data({
    "creative_script": [
        {"id": "5", "name": "DeepSeek V4 (GPUGeek)", "provider": "gpugeek", "model": "Vendor3/DeepSeek-V4-Flash", "icon": "", "description": "DeepSeek's latest model via GPUGeek proxy with excellent reasoning and creative writing."},
        {"id": "6", "name": "P3D", "provider": "p3d", "model": "p3d-codec-engine", "icon": "", "description": "3D codec and engine technologies are designed to significantly improve the performance, efficiency, and controllability of AI-generated video, 3D simulations, and content ecosystems."},
        {"id": "4", "name": "Doubao Pro", "provider": "volcengine", "model": "doubao-seed-2-0-lite-260428", "icon": "", "description": "ByteDance's large language model optimized for Chinese-language creative content."},
        {"id": "1", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hunyuan-turbos-latest", "icon": "", "description": "Tencent's powerful large language model with excellent Chinese creative writing and reasoning."},
        {"id": "2", "name": "Gemini 2.5 Pro", "provider": "google", "model": "gemini-2.5-pro", "icon": "", "description": "Google's most capable model for complex reasoning, coding, and creative writing tasks."},
        {"id": "3", "name": "GPT-4o", "provider": "openai", "model": "gpt-4o", "icon": "", "description": "OpenAI's fast multimodal flagship model with strong creative writing capabilities."},
    ],
    "creative_episode": [],
    "creative_scenes": [
        {"id": "cs_1", "name": "Gemini 2.5 Flash", "provider": "google", "model": "gemini-2.5-flash", "icon": "", "description": "Fast and efficient model for scene breakdown and structuring tasks."},
        {"id": "cs_2", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hunyuan-turbos-latest", "icon": "", "description": "Tencent's efficient model for scene structuring and plot development."},
    ],
    "creative_storyboards": [
        {"id": "sb_1", "name": "Gemini 2.5 Pro", "provider": "google", "model": "gemini-2.5-pro", "icon": "", "description": "High-quality storyboard generation with detailed visual descriptions."},
        {"id": "sb_2", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hunyuan-turbos-latest", "icon": "", "description": "Tencent's model for storyboard layout and visual planning."},
    ],
    "drama_cover": [],
    "scene_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "ByteDance's high-quality image generation model for cinematic scene creation."},
        {"id": "2", "name": "Nanobanana (Google)", "provider": "google", "model": "nanobanana", "icon": "", "description": "Google's efficient image generation model with fast inference speeds."},
        {"id": "4", "name": "Seedream 5.0 (GPUGeek)", "provider": "gpugeek", "model": "Volcengine/Doubao-Seedream-5.0-lite", "icon": "", "description": "ByteDance's Seedream via GPUGeek proxy for high-quality image generation."},
    ],
    "actor_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "High-quality character image generation with consistent facial features."},
        {"id": "2", "name": "Nanobanana (Google)", "provider": "google", "model": "nanobanana", "icon": "", "description": "Fast character portrait generation with good detail preservation."},
        {"id": "4", "name": "Seedream 5.0 (GPUGeek)", "provider": "gpugeek", "model": "Volcengine/Doubao-Seedream-5.0-lite", "icon": "", "description": "ByteDance's Seedream via GPUGeek proxy with consistent facial features."},
    ],
    "actor_three_view_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "Generate consistent three-view character reference sheets for animation."},
        {"id": "4", "name": "Seedream 5.0 (GPUGeek)", "provider": "gpugeek", "model": "Volcengine/Doubao-Seedream-5.0-lite", "icon": "", "description": "ByteDance's Seedream via GPUGeek proxy for character reference sheets."},
    ],
    "storyboard_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "High-quality storyboard frame generation with cinematic composition."},
        {"id": "2", "name": "Nanobanana (Google)", "provider": "google", "model": "nanobanana", "icon": "", "description": "Fast storyboard image generation for rapid prototyping."},
        {"id": "3", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hy-image-v3.0", "icon": "", "description": "Tencent's powerful image generation model with strong text-to-image capabilities."},
        {"id": "4", "name": "Seedream 5.0 (GPUGeek)", "provider": "gpugeek", "model": "Volcengine/Doubao-Seedream-5.0-lite", "icon": "", "description": "ByteDance's Seedream via GPUGeek proxy for cinematic storyboard frames."},
    ],
    "character_look_costume": [],
    "actor_costume": [],
    "actor_costume_three_view": [],
    "prop_image": [],
    "prop_three_view_image": [],
    "storyboard_video": [
        {"id": "1", "name": "Seedance 1.5 Pro", "provider": "volcengine", "model": "seedance-1.5-pro", "icon": "", "description": "ByteDance's professional video generation model with smooth motion and high fidelity."},
        {"id": "2", "name": "Veo 3 (Google)", "provider": "google", "model": "veo-3", "icon": "", "description": "Google's state-of-the-art video generation model with exceptional quality and consistency."},
        {"id": "3", "name": "Seedance 2.0 (GPUGeek)", "provider": "gpugeek", "model": "Volcengine/Doubao-Seedance-2.0-fast", "icon": "", "description": "ByteDance's Seedance via GPUGeek proxy for smooth video generation."},
    ],
    "dialogue_voice": [],
    "storyboard_narration_voice": [],
    "storyboard_sfx_voice": [],
    "storyboard_music_voice": [],
    "creative_video": [
        {"id": "1", "name": "Seedance 1.5 Pro", "provider": "volcengine", "model": "seedance-1.5-pro", "icon": "", "description": "Professional video generation with flexible style control and high output quality."},
        {"id": "2", "name": "Veo 3 (Google)", "provider": "google", "model": "veo-3", "icon": "", "description": "Google's flagship video model, excelling at complex scenes and natural motion."},
        {"id": "3", "name": "Seedance 2.0 (GPUGeek)", "provider": "gpugeek", "model": "Volcengine/Doubao-Seedance-2.0-fast", "icon": "", "description": "ByteDance's Seedance via GPUGeek proxy with professional video generation quality."},
    ],
})

STYLES_DATA = [
    {"id": "cinematic", "name": "Cinematic", "classify": "cinematic", "image": _style_img("#1a1a2e", "#16213e")},
    {"id": "anime", "name": "Anime Style", "classify": "anime", "image": _style_img("#ff6b9d", "#c44dff")},
    {"id": "storybook", "name": "Storybook Illustration", "classify": "realistic", "image": _style_img("#ff9a56", "#ffd166")},
    {"id": "realistic", "name": "Photorealistic", "classify": "realistic", "image": _style_img("#2d6a4f", "#52b788")},
    {"id": "watercolor", "name": "Watercolor", "classify": "cinematic", "image": _style_img("#a8d8ea", "#aa96da")},
    {"id": "3d_render", "name": "3D Render", "classify": "cinematic", "image": _style_img("#0f4c75", "#3282b8")},
    {"id": "pixel_art", "name": "Pixel Art", "classify": "anime", "image": _style_img("#533a71", "#6184d8")},
    {"id": "comic", "name": "Comic Book", "classify": "anime", "image": _style_img("#e63946", "#1d3557")},
]

CONFIG_DATA = {
    "web_name": "VixP3D",
    "web_title": "一键式长篇创作平台",
    "copyright": "VixP3D",
    "version_name": "0.1.0",
    "version": 1,
}


# --- Endpoints ---
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/script2video")
async def script2video(req: Script2VideoRequest):
    """Submit a script-to-video generation task."""
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "script2video", "pending"),
        )
    _track_background_task(run_script2video(task_id, req))
    return success_response(
        TaskResponse(task_id=task_id, mode="script2video", status="pending").model_dump()
    )


@app.post("/api/idea2video")
async def idea2video(req: Idea2VideoRequest):
    """Submit an idea-to-video generation task."""
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "idea2video", "pending"),
        )
    _track_background_task(run_idea2video(task_id, req))
    return success_response(
        TaskResponse(task_id=task_id, mode="idea2video", status="pending").model_dump()
    )


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Query the status of a submitted task."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT task_id, mode, status, result, error FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return success_response({
        "task_id": row["task_id"],
        "mode": row["mode"],
        "status": row["status"],
        "result": row["result"],
        "error": row["error"],
    })


@app.get("/api/tasks")
async def list_tasks():
    """List all tasks."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT task_id, mode, status, result, error FROM tasks ORDER BY created_at DESC"
        ).fetchall()
    return success_response([
        {
            "task_id": r["task_id"],
            "mode": r["mode"],
            "status": r["status"],
            "result": r["result"],
            "error": r["error"],
        }
        for r in rows
    ])


@app.get("/api/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE endpoint for real-time task progress streaming."""
    pm = ProgressManager.get_instance()

    def _terminal_event_from_db() -> Optional[dict]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT status, result, error FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        if row["status"] == "completed":
            return {"type": "complete", "result": row["result"]}
        if row["status"] == "failed":
            return {"type": "error", "error": row["error"] or "Task failed"}
        return None

    async def event_generator():
        index = 0
        heartbeat_interval = 15  # seconds between heartbeats when idle
        last_data_time = time.time()
        try:
            # Send initial connect event so frontend knows the stream is live
            yield f"data: {json_module.dumps({'type': 'connected', 'task_id': task_id}, ensure_ascii=False)}\n\n"

            # Replay buffered in-memory events first (supports reconnect within same process)
            buffered = pm.get_events(task_id)
            for event in buffered:
                yield f"data: {json_module.dumps(event, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)
                if event.get("type") in ("complete", "error"):
                    return
            index = len(buffered)

            terminal = _terminal_event_from_db()
            if terminal and not pm.is_completed(task_id):
                yield f"data: {json_module.dumps(terminal, ensure_ascii=False)}\n\n"
                return
            if pm.is_completed(task_id):
                return

            while True:
                # Wait for new events, or timeout for heartbeat
                try:
                    await pm.subscribe(task_id, from_index=index, timeout=heartbeat_interval)
                except asyncio.CancelledError:
                    return  # Client disconnected

                # Get events (may have arrived during wait)
                events = pm.get_events(task_id)
                new_events = events[index:]

                if new_events:
                    for event in new_events:
                        # Each yield is a potential disconnection point
                        yield f"data: {json_module.dumps(event, ensure_ascii=False)}\n\n"
                        # Yield control to allow cancellation to propagate
                        await asyncio.sleep(0)
                        if event.get("type") in ("complete", "error"):
                            return
                    index = len(events)
                    last_data_time = time.time()

                if pm.is_completed(task_id):
                    return

                terminal = _terminal_event_from_db()
                if terminal:
                    yield f"data: {json_module.dumps(terminal, ensure_ascii=False)}\n\n"
                    return

                # Send heartbeat only when no data has been sent recently
                if time.time() - last_data_time >= heartbeat_interval:
                    yield f": heartbeat {int(time.time())}\n\n"
                    await asyncio.sleep(0)
                    last_data_time = time.time()

        except asyncio.CancelledError:
            pass  # Client disconnected, clean exit

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/tasks/{task_id}/files/{file_path:path}")
async def serve_task_file(task_id: str, file_path: str):
    """Serve an intermediate file from a task's working directory."""
    pm = ProgressManager.get_instance()
    working_dir = pm.get_working_dir(task_id)

    if not working_dir:
        # Fall back to DB lookup
        with get_db() as conn:
            row = conn.execute(
                "SELECT working_dir FROM tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        if row and row["working_dir"]:
            working_dir = row["working_dir"]

    if not working_dir:
        raise HTTPException(status_code=404, detail="Task not found")

    full_path = os.path.normpath(os.path.join(working_dir, file_path))
    norm_working = os.path.normpath(os.path.abspath(working_dir))
    norm_full = os.path.normpath(os.path.abspath(full_path))

    # Security: ensure the resolved path stays within working_dir
    if os.path.commonpath([norm_working, norm_full]) != norm_working:
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(full_path)


@app.get("/api/models")
async def get_models():
    """Get available AI models grouped by scene type."""
    return success_response(MODELS_DATA)


@app.get("/api/styles")
async def get_styles():
    """Get available visual styles."""
    return success_response(STYLES_DATA)


# --- Legacy frontend request model ---
class LegacySubmitRequest(BaseModel):
    """Request model matching the legacy frontend form payload."""
    model_config = {"protected_namespaces": ()}
    model: str = ""
    script: str = "drama"
    title: str = ""
    cover: str = ""
    description: str = ""
    import_: str = Field(default="", validation_alias="import")
    prompt: str = ""
    style: str = ""
    aspect_ratio: str = "9:16"
    episode_sum: int = 1
    episode_duration: int = 10
    resolution: str = "480p"


@app.post("/app/shortplay/api/Index/submit")
async def legacy_submit(
    req: LegacySubmitRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Handle creative mode submit from legacy frontend.
    Maps to idea2video or script2video based on req.script field.
    """
    from pipelines.idea2video_pipeline import build_effective_user_requirement

    user = _optional_user(authorization)
    task_id = str(uuid.uuid4())
    work_title = _task_title(req.title, req.prompt)

    # Build user_requirement from optional fields
    user_requirement_parts = []
    if req.title:
        user_requirement_parts.append(f"Title: {req.title}")
    if req.description:
        user_requirement_parts.append(f"Description: {req.description}")
    base_requirement = "; ".join(user_requirement_parts) if user_requirement_parts else ""
    episode_duration = req.episode_duration if req.episode_duration > 0 else 10
    logging.info(
        "legacy_submit mode=%s episode_duration=%ss aspect_ratio=%s resolution=%s",
        req.script,
        episode_duration,
        req.aspect_ratio,
        req.resolution,
    )
    user_requirement = build_effective_user_requirement(
        base_requirement,
        episode_count=1,
        episode_duration=episode_duration,
        aspect_ratio=req.aspect_ratio,
    )
    episode_count = 1

    if req.script == "script":
        script_req = Script2VideoRequest(
            script=req.prompt,
            user_requirement=user_requirement,
            style=req.style or "Cinematic",
            config_path=_default_pipeline_config("script2video"),
            model_id=req.model,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
            episode_duration=episode_duration,
        )
        mode = "script2video"
        with get_db() as conn:
            _insert_task(
                conn,
                task_id=task_id,
                mode=mode,
                user_id=user["id"] if user else None,
                title=work_title,
                prompt=req.prompt,
            )
        _track_background_task(run_script2video(task_id, script_req))
    else:
        idea_req = Idea2VideoRequest(
            idea=req.prompt,
            user_requirement=user_requirement,
            style=req.style or "Cinematic",
            config_path=_default_pipeline_config("idea2video"),
            model_id=req.model,
            episode_count=episode_count,
            episode_duration=episode_duration,
            aspect_ratio=req.aspect_ratio,
            resolution=req.resolution,
        )
        mode = "idea2video"
        with get_db() as conn:
            _insert_task(
                conn,
                task_id=task_id,
                mode=mode,
                user_id=user["id"] if user else None,
                title=work_title,
                prompt=req.prompt,
            )
        _track_background_task(run_idea2video(task_id, idea_req))

    return success_response({"uuid": task_id, "task_id": task_id, "mode": mode})


@app.get("/app/model/api/Model/models")
async def legacy_get_models():
    """Get available AI models (legacy frontend endpoint)."""
    return success_response(MODELS_DATA)


@app.get("/app/shortplay/api/Style/index")
async def legacy_get_styles(classify: str = "all", name: str = ""):
    """Get available visual styles with filtering (legacy frontend endpoint)."""
    styles = STYLES_DATA
    if classify and classify != "all":
        styles = [s for s in styles if s.get("classify") == classify]
    if name:
        styles = [s for s in styles if name.lower() in s["name"].lower()]
    return success_response(styles)


@app.get("/api/config")
async def get_config():
    """Get site configuration."""
    return success_response(CONFIG_DATA)


# --- Request models for generation endpoints ---
class GenerateSceneImageRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: Optional[str] = None
    drama_id: Optional[str] = None
    episode_id: Optional[str] = None
    scene_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    model_id: Optional[str] = None
    image_url: Optional[str] = None


class GenerateStoryboardImageRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    drama_id: Optional[str] = None
    episode_id: Optional[str] = None
    storyboard_id: Optional[str] = None
    prompt: Optional[str] = None
    model_id: Optional[str] = None
    first_image: Optional[str] = None
    last_image: Optional[str] = None


class GenerateStoryboardVideoRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    drama_id: Optional[str] = None
    episode_id: Optional[str] = None
    storyboard_id: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    first_image: Optional[str] = None
    last_image: Optional[str] = None
    duration: int = 5
    model_id: Optional[str] = None


class GenerateCharacterLookRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    actor_id: Optional[str] = None
    drama_id: Optional[str] = None
    prompt: Optional[str] = None
    model_id: Optional[str] = None


class GenerateDramaCoverRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    drama_id: Optional[str] = None
    prompt: Optional[str] = None
    model_id: Optional[str] = None


class CreativeVideoRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    image_url: str
    prompt: str = ""
    duration: int = 5
    resolution: str = "1080p"
    model_id: Optional[str] = None


class TaskSearchRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    scene: Optional[str] = None
    drama_id: Optional[str] = None
    episode_id: Optional[str] = None
    limit: int = 20
    page: int = 1


class VoiceModelResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    name: str
    language: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None


# --- Frontend-facing endpoints under /app/ paths ---

# --- Tasks (frontend-facing) ---
@app.get("/app/model/api/Task/index")
async def frontend_task_list(
    scene: Optional[str] = None,
    drama_id: Optional[str] = None,
    episode_id: Optional[str] = None,
    limit: int = 20,
    page: int = 1,
):
    """List tasks with optional filtering (frontend endpoint)."""
    with get_db() as conn:
        query = "SELECT task_id, mode, status, result, error, created_at FROM tasks"
        params: list = []
        where_clauses = []
        if scene:
            where_clauses.append("mode = ?")
            params.append(scene)
        if drama_id:
            where_clauses.append("task_id LIKE ?")
            params.append(f"%{drama_id}%")
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, (page - 1) * limit])
        rows = conn.execute(query, params).fetchall()
        items = [
            {
                "task_id": r["task_id"],
                "mode": r["mode"],
                "status": r["status"],
                "result": r["result"],
                "error": r["error"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
        # Get total count (inside the with block)
        count_query = "SELECT COUNT(*) FROM tasks"
        count_params: list = []
        if where_clauses:
            count_query += " WHERE " + " AND ".join(where_clauses)
            if scene:
                count_params.append(scene)
            if drama_id:
                count_params.append(f"%{drama_id}%")
        total = conn.execute(count_query, count_params).fetchone()[0]
    return success_response({"data": items, "total": total, "page": page, "limit": limit})


async def run_scene_image_generation(
    task_id: str,
    prompt: str,
    image_url: Optional[str],
    model_id: Optional[str],
):
    """Run scene image generation in background."""
    pm = ProgressManager.get_instance()
    log_handler = _install_log_handler(task_id)
    ref_path = None
    try:
        output_dir = _backend_path(".working_dir", "scenes")
        os.makedirs(output_dir, exist_ok=True)
        pm.set_working_dir(task_id, output_dir)
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET working_dir = ? WHERE task_id = ?",
                (output_dir, task_id),
            )

        pm.emit(task_id, {"type": "stage_start", "stage": "scene_image", "message": "Starting scene image generation..."})

        gen = _get_image_generator(model_id)
        ref_paths = []
        if image_url:
            ref_path = await _download_image(image_url)
            ref_paths = [ref_path]

        # Check generator type to pass correct size parameter
        gen_class_name = type(gen).__name__
        if "Nanobanana" in gen_class_name or "nanobanana" in gen_class_name.lower():
            result = await gen.generate_single_image(
                prompt=prompt,
                reference_image_paths=ref_paths,
                aspect_ratio="16:9",
            )
        else:
            result = await gen.generate_single_image(
                prompt=prompt,
                reference_image_paths=ref_paths,
                size="1600x900",
            )

        # Save image
        output_path = os.path.join(output_dir, f"scene_{task_id}.png")
        result.save(output_path)

        logging.info(f"Scene image saved to {output_path}")
        pm.emit(task_id, {
            "type": "artifact",
            "stage": "scene_image",
            "file_type": "image",
            "file_path": f"scene_{task_id}.png",
            "url": f"/api/tasks/{task_id}/files/scene_{task_id}.png",
        })
        pm.emit(task_id, {"type": "stage_end", "stage": "scene_image", "message": "Scene image generated"})
        pm.emit(task_id, {"type": "complete", "result": output_path})

        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", output_path, task_id),
            )
    except Exception as e:
        logging.exception(f"Scene image generation failed for task {task_id}")
        pm.emit(task_id, {"type": "error", "error": format_exception(e)})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", format_exception(e), task_id),
            )
    finally:
        _remove_log_handler(log_handler)
        # Clean up temp reference image
        if ref_path and os.path.exists(ref_path):
            try:
                os.remove(ref_path)
            except OSError:
                pass


async def run_storyboard_image_generation(
    task_id: str,
    prompt: str,
    model_id: Optional[str],
    first_image: Optional[str] = None,
    last_image: Optional[str] = None,
):
    """Run storyboard image generation in background."""
    pm = ProgressManager.get_instance()
    log_handler = _install_log_handler(task_id)
    ref_paths = []
    try:
        output_dir = _backend_path(".working_dir", "storyboards")
        os.makedirs(output_dir, exist_ok=True)
        pm.set_working_dir(task_id, output_dir)
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET working_dir = ? WHERE task_id = ?",
                (output_dir, task_id),
            )

        pm.emit(task_id, {"type": "stage_start", "stage": "storyboard_image", "message": "Starting storyboard image generation..."})

        gen = _get_image_generator(model_id)
        if first_image:
            ref_paths.append(await _download_image(first_image))
        if last_image:
            ref_paths.append(await _download_image(last_image))

        gen_class_name = type(gen).__name__
        if "Nanobanana" in gen_class_name or "nanobanana" in gen_class_name.lower():
            result = await gen.generate_single_image(
                prompt=prompt,
                reference_image_paths=ref_paths,
                aspect_ratio="16:9",
            )
        else:
            result = await gen.generate_single_image(
                prompt=prompt,
                reference_image_paths=ref_paths,
                size="1600x900",
            )

        output_path = os.path.join(output_dir, f"storyboard_{task_id}.png")
        result.save(output_path)

        logging.info(f"Storyboard image saved to {output_path}")
        pm.emit(task_id, {
            "type": "artifact",
            "stage": "storyboard_image",
            "file_type": "image",
            "file_path": f"storyboard_{task_id}.png",
            "url": f"/api/tasks/{task_id}/files/storyboard_{task_id}.png",
        })
        pm.emit(task_id, {"type": "stage_end", "stage": "storyboard_image", "message": "Storyboard image generated"})
        pm.emit(task_id, {"type": "complete", "result": output_path})

        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", output_path, task_id),
            )
    except Exception as e:
        logging.exception(f"Storyboard image generation failed for task {task_id}")
        pm.emit(task_id, {"type": "error", "error": format_exception(e)})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", format_exception(e), task_id),
            )
    finally:
        _remove_log_handler(log_handler)
        for p in ref_paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


async def run_video_generation(
    task_id: str,
    mode: str,
    stage: str,
    prompt: str,
    model_id: Optional[str],
    reference_urls: Optional[list[str]] = None,
    duration: int = 5,
    resolution: str = "1080p",
    output_prefix: str = "video",
):
    """Run image-to-video or text-to-video generation in background."""
    pm = ProgressManager.get_instance()
    log_handler = _install_log_handler(task_id)
    ref_paths: list[str] = []
    try:
        output_dir = _backend_path(".working_dir", mode)
        os.makedirs(output_dir, exist_ok=True)
        pm.set_working_dir(task_id, output_dir)
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET working_dir = ? WHERE task_id = ?",
                (output_dir, task_id),
            )

        pm.emit(task_id, {"type": "stage_start", "stage": stage, "message": f"Starting {stage}..."})

        gen = _get_video_generator(model_id)
        for url in reference_urls or []:
            if url:
                ref_paths.append(await _download_image(url))

        duration_val = 5 if duration <= 5 else 10
        result = await gen.generate_single_video(
            prompt=prompt or "Generate a cinematic video clip.",
            reference_image_paths=ref_paths,
            resolution=resolution if resolution in ("480p", "720p", "1080p") else "1080p",
            duration=duration_val,
        )

        output_path = os.path.join(output_dir, f"{output_prefix}_{task_id}.mp4")
        result.save(output_path)

        rel_name = f"{output_prefix}_{task_id}.mp4"
        pm.emit(task_id, {
            "type": "artifact",
            "stage": stage,
            "file_type": "video",
            "file_path": rel_name,
            "url": f"/api/tasks/{task_id}/files/{rel_name}",
        })
        pm.emit(task_id, {"type": "stage_end", "stage": stage, "message": f"{stage} completed"})
        pm.emit(task_id, {"type": "complete", "result": output_path})

        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", output_path, task_id),
            )
    except Exception as e:
        logging.exception(f"{stage} failed for task {task_id}")
        pm.emit(task_id, {"type": "error", "error": format_exception(e)})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", format_exception(e), task_id),
            )
    finally:
        _remove_log_handler(log_handler)
        for p in ref_paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


async def run_image_generation_task(
    task_id: str,
    mode: str,
    stage: str,
    prompt: str,
    model_id: Optional[str],
    output_prefix: str,
):
    """Generic single-image generation used by character look and drama cover."""
    pm = ProgressManager.get_instance()
    log_handler = _install_log_handler(task_id)
    try:
        output_dir = _backend_path(".working_dir", mode)
        os.makedirs(output_dir, exist_ok=True)
        pm.set_working_dir(task_id, output_dir)
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET working_dir = ? WHERE task_id = ?",
                (output_dir, task_id),
            )

        pm.emit(task_id, {"type": "stage_start", "stage": stage, "message": f"Starting {stage}..."})
        gen = _get_image_generator(model_id)
        gen_class_name = type(gen).__name__
        if "Nanobanana" in gen_class_name or "nanobanana" in gen_class_name.lower():
            result = await gen.generate_single_image(prompt=prompt, reference_image_paths=[], aspect_ratio="16:9")
        else:
            result = await gen.generate_single_image(prompt=prompt, reference_image_paths=[], size="1600x900")

        output_path = os.path.join(output_dir, f"{output_prefix}_{task_id}.png")
        result.save(output_path)
        rel_name = f"{output_prefix}_{task_id}.png"
        pm.emit(task_id, {
            "type": "artifact",
            "stage": stage,
            "file_type": "image",
            "file_path": rel_name,
            "url": f"/api/tasks/{task_id}/files/{rel_name}",
        })
        pm.emit(task_id, {"type": "stage_end", "stage": stage, "message": f"{stage} completed"})
        pm.emit(task_id, {"type": "complete", "result": output_path})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", output_path, task_id),
            )
    except Exception as e:
        logging.exception(f"{stage} failed for task {task_id}")
        pm.emit(task_id, {"type": "error", "error": format_exception(e)})
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", format_exception(e), task_id),
            )
    finally:
        _remove_log_handler(log_handler)


# --- Generation endpoints ---

@app.post("/app/shortplay/api/Generate/sceneImage")
async def generate_scene_image(req: GenerateSceneImageRequest):
    """Generate a scene image from prompt and optional reference image."""
    prompt = req.prompt or req.description or ""
    if not prompt:
        return success_response({"task_id": None, "status": "failed", "error": "prompt or description is required"})

    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "scene_image", "pending"),
        )
    _track_background_task(run_scene_image_generation(
        task_id, prompt, req.image_url, req.model_id
    ))
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Generate/storyboardImage")
async def generate_storyboard_image(req: GenerateStoryboardImageRequest):
    """Generate a storyboard image. Returns a task_id for async processing."""
    prompt = req.prompt or ""
    if not prompt:
        return success_response({"task_id": None, "status": "failed", "error": "prompt is required"})

    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "storyboard_image", "pending"),
        )
    _track_background_task(run_storyboard_image_generation(
        task_id, prompt, req.model_id, req.first_image, req.last_image
    ))
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Generate/storyboardVideo")
async def generate_storyboard_video(req: GenerateStoryboardVideoRequest):
    """Generate a storyboard video. Returns a task_id for async processing."""
    prompt = req.prompt or ""
    if not prompt and not req.first_image:
        return error_response(400, "prompt or first_image is required")

    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "storyboard_video", "pending"),
        )
    refs = [u for u in [req.first_image, req.last_image] if u]
    _track_background_task(run_video_generation(
        task_id,
        mode="storyboard_video",
        stage="storyboard_video",
        prompt=prompt,
        model_id=req.model_id,
        reference_urls=refs,
        duration=req.duration,
        output_prefix="storyboard",
    ))
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Generate/characterLook")
async def generate_character_look(req: GenerateCharacterLookRequest):
    """Generate character look images. Returns a task_id for async processing."""
    prompt = req.prompt or "Generate a character portrait with consistent features."
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "character_look", "pending"),
        )
    _track_background_task(run_image_generation_task(
        task_id, "character_look", "character_look", prompt, req.model_id, "character_look"
    ))
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Generate/dramaCover")
async def generate_drama_cover(req: GenerateDramaCoverRequest):
    """Generate a drama cover image. Returns a task_id for async processing."""
    prompt = req.prompt or "Generate a cinematic drama cover poster."
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "drama_cover", "pending"),
        )
    _track_background_task(run_image_generation_task(
        task_id, "drama_cover", "drama_cover", prompt, req.model_id, "drama_cover"
    ))
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Creative/video")
async def creative_video(req: CreativeVideoRequest):
    """Generate a video from image + prompt (creative mode). Returns a task_id."""
    if not req.image_url:
        return error_response(400, "image_url is required")
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "creative_video", "pending"),
        )
    _track_background_task(run_video_generation(
        task_id,
        mode="creative_video",
        stage="creative_video",
        prompt=req.prompt,
        model_id=req.model_id,
        reference_urls=[req.image_url],
        duration=req.duration,
        resolution=req.resolution,
        output_prefix="creative",
    ))
    return success_response({"task_id": task_id, "status": "pending"})


# --- Voice ---
VOICE_MODELS = [
    {"id": "1", "name": "Female - Warm", "language": "zh-CN", "gender": "female", "age": "adult"},
    {"id": "2", "name": "Male - Deep", "language": "zh-CN", "gender": "male", "age": "adult"},
    {"id": "3", "name": "Female - Sweet", "language": "en", "gender": "female", "age": "young"},
    {"id": "4", "name": "Male - Clear", "language": "en", "gender": "male", "age": "adult"},
]


@app.get("/app/model/api/Voice/modelList")
async def get_voice_models():
    """Get available voice models."""
    return success_response(VOICE_MODELS)


@app.get("/app/shortplay/api/Voice/list")
async def get_voice_list():
    """Get voice list."""
    return success_response({"data": VOICE_MODELS, "total": len(VOICE_MODELS)})


# --- Upload ---
def _safe_upload_subdir(dir_name: str) -> Optional[str]:
    safe = (dir_name or "uploads").strip().strip("/")
    if not safe or ".." in safe or not _SAFE_DIR_RE.match(safe):
        return None
    return safe


def _resolve_upload_path(url: str) -> Optional[str]:
    """Map a /api/uploads/... URL back to a local file path (with traversal guard)."""
    if not url or not url.startswith("/api/uploads/"):
        return None
    rel = url[len("/api/uploads/"):]
    full = os.path.normpath(os.path.join(UPLOADS_DIR, rel))
    base = os.path.normpath(os.path.abspath(UPLOADS_DIR))
    if os.path.commonpath([base, os.path.abspath(full)]) != base:
        return None
    return full if os.path.exists(full) else None


async def _resolve_image_path(url: str) -> Optional[str]:
    """Resolve a reference image URL to a local path, downloading remote URLs."""
    if not url:
        return None
    local = _resolve_upload_path(url)
    if local:
        return local
    if url.startswith(("http://", "https://")):
        return await _download_image(url)
    return None


@app.post("/app/shortplay/api/Uploads/upload")
async def upload_file(
    file: UploadFile = File(...),
    dir_name: str = Form("uploads"),
    dir_title: str = Form(""),
    authorization: Optional[str] = Header(default=None),
):
    """Upload an image and return its servable URL."""
    _require_user(authorization)
    safe_dir = _safe_upload_subdir(dir_name)
    if safe_dir is None:
        return error_response(400, "非法的上传目录")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTS:
        return error_response(400, "仅支持 PNG/JPG/JPEG/WEBP/GIF 图片")
    target_dir = os.path.join(UPLOADS_DIR, safe_dir)
    os.makedirs(target_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    content = await file.read()
    with open(os.path.join(target_dir, filename), "wb") as f:
        f.write(content)
    return success_response({
        "url": f"/api/uploads/{safe_dir}/{filename}",
        "dir_name": dir_name,
        "dir_title": dir_title,
        "name": filename,
    })


@app.get("/api/uploads/{file_path:path}")
async def serve_upload(file_path: str):
    """Serve an uploaded/generated media file."""
    full = os.path.normpath(os.path.join(UPLOADS_DIR, file_path))
    base = os.path.normpath(os.path.abspath(UPLOADS_DIR))
    if os.path.commonpath([base, os.path.abspath(full)]) != base:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full)


# ===================================================================
# Frontend stub endpoints — 提供给前端的接口桩，返回写死的数据
# ===================================================================

CONTROL_CONFIG_DATA = {
    "web_name": "VixP3D",
    "web_title": "一键式长篇创作平台",
    "web_logo": "",
    "web_icp": "",
    "web_mps": "",
    "web_mps_text": "",
    "copyright": "VixP3D",
    "version_name": "0.1.0",
    "version": 1,
    "wechat_group_qrcode_url": "",
    "guide_url": "",
    "project_background_video_url": "",
    "login_background_image_url": "",
    "login": {
        "image": "",
        "bg_image": "off",
    },
    "push": {
        "url": "",
        "app_key": "",
        "auth": "",
    },
    "enum": {
        "actor_species_type": [
            {"value": 1, "label": "人类"},
            {"value": 2, "label": "动物"},
            {"value": 3, "label": "其他"},
        ],
        "actor_gender": [
            {"value": 1, "label": "男"},
            {"value": 2, "label": "女"},
        ],
        "actor_age": [
            {"value": 1, "label": "儿童"},
            {"value": 2, "label": "青年"},
            {"value": 3, "label": "中年"},
            {"value": 4, "label": "老年"},
        ],
        "style_classify": [
            {"value": "all", "label": "全部"},
            {"value": "cinematic", "label": "电影级"},
            {"value": "anime", "label": "动漫"},
            {"value": "realistic", "label": "写实"},
        ],
        "voice_emotion": [
            {"value": "neutral", "label": "中性"},
            {"value": "happy", "label": "开心"},
            {"value": "sad", "label": "悲伤"},
            {"value": "angry", "label": "愤怒"},
        ],
    },
    "showMenu": ["index", "notice", "user"],
}


@app.get("/app/control/api/Public/config")
async def control_config():
    """前端控制面板配置."""
    return success_response(CONTROL_CONFIG_DATA)


@app.post("/app/control/api/Public/getSmsVcode")
async def get_sms_vcode():
    """短信验证码已停用."""
    return error_response(400, "当前仅支持账号密码登录")


def _extract_token(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if not authorization:
        return None
    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token or None


# --- User ---
def _optional_user(authorization: Optional[str]) -> Optional[dict]:
    token = _extract_token(authorization)
    if not token:
        return None
    with get_db() as conn:
        return auth_service.get_user_by_token(conn, token)


def _require_user(authorization: Optional[str]) -> dict:
    user = _optional_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def _task_title(title: str, prompt: str, fallback: str = "未命名作品") -> str:
    cleaned_title = (title or "").strip()
    if cleaned_title:
        return cleaned_title[:80]
    cleaned_prompt = " ".join((prompt or "").split())
    if cleaned_prompt:
        return cleaned_prompt[:80]
    return fallback


def _persist_user_work(task_id: str) -> None:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT user_id, title, prompt, mode, working_dir, result
            FROM tasks WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        if row is None or not row["user_id"]:
            return
        user_works_service.create_work_from_task(
            conn,
            user_id=row["user_id"],
            task_id=task_id,
            title=row["title"] or _task_title("", row["prompt"] or ""),
            prompt=row["prompt"] or "",
            mode=row["mode"] or "idea2video",
            result_path=row["result"] or "",
            working_dir=row["working_dir"],
        )


def _insert_task(
    conn,
    *,
    task_id: str,
    mode: str,
    user_id: Optional[str] = None,
    title: str = "",
    prompt: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO tasks (task_id, mode, status, user_id, title, prompt)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (task_id, mode, "pending", user_id, title, prompt),
    )


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class RegisterRequest(BaseModel):
    username: str = ""
    password: str = ""
    vpassword: str = ""


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None


@app.get("/app/user/api/User/info")
async def user_info(authorization: Optional[str] = Header(default=None)):
    """Return the authenticated user profile."""
    token = _extract_token(authorization)
    with get_db() as conn:
        user = auth_service.get_user_by_token(conn, token)
    if user is None:
        return success_response({"token": "", "is_guest": False})
    return success_response(user)


@app.post("/app/user/api/User/update")
async def user_update(
    req: UserUpdateRequest,
    authorization: Optional[str] = Header(default=None),
):
    token = _extract_token(authorization)
    with get_db() as conn:
        user = auth_service.get_user_by_token(conn, token)
        if user is None:
            return error_response(12000, "请先登录")
        if req.nickname and req.nickname.strip():
            conn.execute(
                "UPDATE users SET nickname = ? WHERE id = ?",
                (req.nickname.strip(), user["id"]),
            )
            user = auth_service.get_user_by_token(conn, token)
    return success_response(user)


@app.post("/app/user/api/User/bindMobile")
async def bind_mobile(authorization: Optional[str] = Header(default=None)):
    """Mobile binding is disabled; username/password auth only."""
    token = _extract_token(authorization)
    with get_db() as conn:
        user = auth_service.get_user_by_token(conn, token)
    if user is None:
        return error_response(12000, "请先登录")
    return error_response(400, "当前仅支持账号密码登录，无需绑定手机号")


@app.post("/app/user/api/User/bindInvitationCode")
async def bind_invitation_code():
    """绑定邀请码（桩）."""
    return success_response({})


@app.get("/app/user/api/User/checkInvitationCode")
async def check_invitation_code(code: str = ""):
    """检查邀请码（桩）."""
    return success_response({"valid": True})


@app.get("/app/user/api/User/getUnusedInvitationCode")
async def get_unused_invitation_code():
    """获取未使用的邀请码（桩）."""
    return success_response([])


@app.post("/app/user/api/Login/login")
async def login(req: LoginRequest):
    try:
        with get_db() as conn:
            user, _token = auth_service.login_user(conn, req.username, req.password)
        return success_response(user)
    except ValueError as e:
        return error_response(400, format_exception(e))


@app.post("/app/user/api/Login/register")
async def register(req: RegisterRequest):
    if req.password != req.vpassword:
        return error_response(400, "两次输入的密码不一致")
    try:
        with get_db() as conn:
            user, _token = auth_service.register_user(conn, req.username, req.password)
        return success_response(user)
    except ValueError as e:
        return error_response(400, format_exception(e))


@app.post("/app/user/api/Login/loginPass")
@app.post("/app/user/api/Login/loginSms")
@app.post("/app/user/api/Login/wechatLogin")
@app.post("/app/user/api/Login/vcode")
async def login_legacy_disabled():
    return error_response(400, "当前仅支持账号密码登录")


@app.get("/app/user/api/Captcha/captcha_json")
async def captcha():
    """图形验证码（已停用）."""
    return error_response(400, "当前仅支持账号密码登录")


# --- Actor ---
@app.get("/app/shortplay/api/Actor/index")
async def actor_list(
    type: str = "all",
    name: str = "",
    species_type: Optional[str] = None,
    gender: Optional[str] = None,
    age: Optional[str] = None,
    drama_id: str = "",
    episode_id: str = "",
    authorization: Optional[str] = Header(default=None),
):
    """演员列表."""
    user = _optional_user(authorization)
    if user is None:
        return success_response([])
    with get_db() as conn:
        items = actors_service.list_actors(
            conn,
            user["id"],
            type=type,
            name=name,
            species_type=species_type,
            gender=gender,
            age=age,
            drama_id=drama_id,
            episode_id=episode_id,
        )
    return success_response(items)


class ActorDeleteRequest(BaseModel):
    id: str


@app.post("/app/shortplay/api/Actor/update")
async def actor_update(
    req: Request,
    authorization: Optional[str] = Header(default=None),
):
    """新增或编辑演员."""
    user = _require_user(authorization)
    data = await req.json()
    with get_db() as conn:
        actor = actors_service.upsert_actor(conn, user["id"], data)
    return success_response(actor)


@app.post("/app/shortplay/api/Actor/delete")
async def actor_delete(
    req: ActorDeleteRequest,
    authorization: Optional[str] = Header(default=None),
):
    """删除演员."""
    user = _require_user(authorization)
    with get_db() as conn:
        deleted = actors_service.delete_actor(conn, user["id"], req.id)
    if not deleted:
        return error_response(404, "演员不存在或无权删除")
    return success_response({})


@app.post("/app/shortplay/api/Actor/initializing")
async def actor_initializing(
    req: Request,
    authorization: Optional[str] = Header(default=None),
):
    """Generate an actor's portrait and/or three-view turnaround (synchronous)."""
    user = _require_user(authorization)
    data = await req.json()
    actor_id = (data.get("id") or "").strip()
    if not actor_id:
        return error_response(400, "缺少演员ID")

    with get_db() as conn:
        actor = actors_service.get_actor(conn, user["id"], actor_id)
    if actor is None or not actor["is_edit"]:
        return error_response(404, "演员不存在或无权操作")

    want_image = bool(data.get("image_state")) or bool(data.get("image_model_id"))
    want_three_view = bool(data.get("three_view_image_state")) or bool(data.get("three_view_model_id"))
    if not want_image and not want_three_view:
        return error_response(400, "请至少选择一个出图模型")

    reference_path = None
    if data.get("image_reference_state") and data.get("reference_headimg"):
        reference_path = await _resolve_image_path(data.get("reference_headimg"))

    with get_db() as conn:
        actors_service.set_actor_status(conn, user["id"], actor_id, "pending")

    try:
        model_id = str(data.get("image_model_id") or data.get("three_view_model_id") or "") or None
        generator = _get_image_generator(model_id)
        results = await actor_image.generate_actor_portraits(
            actor={
                **actor,
                "name": data.get("name") or actor["name"],
                "remarks": data.get("remarks") or actor["remarks"],
                "species_type": data.get("species_type") if data.get("species_type") not in (None, "") else actor["species_type"],
            },
            image_generator=generator,
            save_dir=os.path.join(UPLOADS_DIR, "actor", "generated"),
            url_prefix="/api/uploads/actor/generated",
            want_image=want_image,
            want_three_view=want_three_view,
            reference_path=reference_path,
        )
        with get_db() as conn:
            updated = actors_service.update_actor_images(
                conn, user["id"], actor_id, status="success", **results
            )
    except Exception as e:
        logging.exception("actor image generation failed for %s", actor_id)
        with get_db() as conn:
            actors_service.set_actor_status(conn, user["id"], actor_id, "error")
        return error_response(500, format_exception(e))

    return success_response({
        "id": actor_id,
        "status": updated["status"],
        "status_enum": updated["status_enum"],
        "headimg": updated["headimg"],
        "three_view_image": updated["three_view_image"],
    })


# --- Prop (桩) ---
@app.get("/app/shortplay/api/Prop/index")
async def prop_list():
    """道具列表（桩）— returns empty array for mention search."""
    return success_response([])


_EMPTY_LIST = {"data": [], "total": 0}


# --- Works / Drama / Episode ---
@app.get("/app/shortplay/api/Works/index")
async def works_list(
    page: int = 1,
    limit: int = 20,
    title: str = "",
    authorization: Optional[str] = Header(default=None),
):
    user = _optional_user(authorization)
    if user is None:
        return success_response({"data": [], "total": 0, "page": page, "limit": limit})
    with get_db() as conn:
        items, total = user_works_service.list_user_works(
            conn,
            user["id"],
            page=page,
            limit=limit,
            title=title,
        )
    return success_response({"data": items, "total": total, "page": page, "limit": limit})


@app.get("/app/shortplay/api/Works/details")
async def works_details(
    id: str = "",
    authorization: Optional[str] = Header(default=None),
):
    user = _require_user(authorization)
    with get_db() as conn:
        work = user_works_service.get_user_work(conn, user["id"], id)
    if work is None:
        return error_response(404, "作品不存在")
    return success_response(work)


@app.get("/app/shortplay/api/Works/episode")
async def works_episode():
    return success_response(_EMPTY_LIST)


class DramaDeleteRequest(BaseModel):
    id: str


@app.post("/app/shortplay/api/Drama/delete")
async def drama_delete(
    req: DramaDeleteRequest,
    authorization: Optional[str] = Header(default=None),
):
    user = _require_user(authorization)
    with get_db() as conn:
        deleted = user_works_service.delete_user_work(conn, user["id"], req.id)
    if not deleted:
        return error_response(404, "作品不存在")
    return success_response({})


# --- Scene (桩) ---
@app.get("/app/shortplay/api/Scene/index")
async def scene_list():
    return success_response([])


# --- Storyboard (桩) ---
@app.get("/app/shortplay/api/Storyboard/index")
async def storyboard_list():
    return success_response([])


@app.get("/app/shortplay/api/StoryboardDialogue/index")
async def storyboard_dialogue_list():
    return success_response([])


# --- CharacterLook (桩) ---
@app.get("/app/shortplay/api/CharacterLook/index")
async def character_look_list():
    return success_response([])


# --- Square (桩) ---
@app.get("/app/shortplay/api/Square/details")
async def square_details():
    return success_response({})


@app.get("/app/shortplay/api/Square/episodes")
async def square_episodes():
    return success_response(_EMPTY_LIST)


# --- Article (桩) ---
@app.get("/app/article/api/Article/index")
async def article_list():
    return success_response(_EMPTY_LIST)


@app.get("/app/article/api/Article/details")
async def article_details():
    return success_response({})


# --- Notification (桩) ---
@app.get("/app/notification/api/Message/list")
async def message_list():
    return success_response(_EMPTY_LIST)


@app.get("/app/notification/api/Message/detail")
async def message_detail():
    return success_response({})


# --- Voice (桩) ---
@app.post("/app/model/api/Voice/update")
async def voice_update():
    return success_response({})


@app.post("/app/model/api/Voice/submit")
async def voice_submit():
    return success_response({})


@app.get("/app/model/api/VoiceText/index")
async def voice_text_list():
    return success_response(_EMPTY_LIST)


# --- Chunk upload (桩) ---
@app.post("/app/shortplay/api/drama/uploadChunkCheck")
async def upload_chunk_check():
    return success_response({"uploaded": []})


@app.post("/app/shortplay/api/drama/uploadChunk")
async def upload_chunk():
    return success_response({})


@app.post("/app/shortplay/api/drama/mergeChunks")
async def merge_chunks():
    return success_response({"url": "/uploads/placeholder.mp4"})


# ===================================================================
# Catch-all — 以上未匹配的 /app/ 请求统一返回成功（桩）
# ===================================================================
@app.api_route("/app/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def app_catch_all(full_path: str):
    """Unimplemented /app/ endpoints return 501 instead of silent success."""
    return JSONResponse(
        status_code=501,
        content=error_response(501, f"Endpoint not implemented: /app/{full_path}"),
    )


# --- Startup ---
@app.on_event("startup")
async def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn

    init_db()

    # Use the same logging config and expose access log
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    log_config["formatters"]["default"]["datefmt"] = "%H:%M:%S"
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s [%(name)s] %(levelname)s: %(client_addr)s - "%(request_line)s" %(status_code)s'
    log_config["formatters"]["access"]["datefmt"] = "%H:%M:%S"

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVER_PORT,
        log_config=log_config,
        log_level="info",  # uvicorn's own startup messages at info
        access_log=True,   # enable request access log
    )
