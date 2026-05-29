import os
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
# Enable HTTP-level debug logging for LLM API calls
logging.getLogger("openai").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

from dotenv import load_dotenv
# Load .env from the backend directory (next to this file)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import asyncio
import hashlib
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import aiohttp
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

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
      - None -> use config default
    """
    from tools.render_backend import RenderBackend

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Override image generator class based on model_id
    if model_id in ("1", "nanobanana", "google", "gemini"):
        config["image_generator"]["class_path"] = "tools.ImageGeneratorNanobananaGoogleAPI"
    elif model_id in ("2", "seedream", "volcengine", "doubao"):
        config["image_generator"]["class_path"] = "tools.ImageGeneratorDoubaoSeedreamVolcengineAPI"
    elif model_id in ("3", "hunyuan", "tencent"):
        config["image_generator"]["class_path"] = "tools.ImageGeneratorHunyuanTencentAPI"

    backend = RenderBackend.from_config(config)
    return backend.image_generator


async def _download_image(url: str) -> str:
    """Download image from URL to a temp file. Returns file path."""
    ext = ".png"
    if "." in url.split("/")[-1]:
        ext = "." + url.split("/")[-1].split(".")[-1].split("?")[0]
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            ext = ".png"
    fd, path = tempfile.mkstemp(suffix=ext)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            data = await resp.read()
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path

app = FastAPI(
    title="ViMax API",
    description="Agentic Video Generation API - supports script2video and idea2video modes",
    version="0.1.0",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SQLite database ---
DB_PATH = "tasks.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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


# --- Request models ---
class Script2VideoRequest(BaseModel):
    script: str
    user_requirement: str = ""
    style: str = "Cinematic"
    config_path: str = "configs/script2video.yaml"


class Idea2VideoRequest(BaseModel):
    idea: str
    user_requirement: str = ""
    style: str = "Cinematic"
    config_path: str = "configs/idea2video.yaml"
    model_id: str = ""
    episode_count: int = 0  # 0 = let LLM decide; >0 = force this many episodes


class TaskResponse(BaseModel):
    task_id: str
    mode: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


# --- Background runners ---
async def run_script2video(task_id: str, req: Script2VideoRequest):
    Script2VideoPipeline, _ = _import_pipelines()
    try:
        pipeline = Script2VideoPipeline.init_from_config(config_path=req.config_path)
        # Use a deterministic cache key so identical inputs reuse the same cache directory.
        cache_key_raw = "|".join([
            req.script,
            req.user_requirement or "",
            req.style,
            req.config_path,
        ])
        cache_key = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()[:16]
        pipeline.working_dir = os.path.join(pipeline.working_dir, cache_key)
        os.makedirs(pipeline.working_dir, exist_ok=True)
        result_path = await pipeline(
            script=req.script,
            user_requirement=req.user_requirement,
            style=req.style,
        )
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", result_path, task_id),
            )
    except Exception as e:
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", str(e), task_id),
            )


def _find_model_by_id(model_id: str) -> dict | None:
    """Find a model entry in MODELS_DATA by its id."""
    if not model_id:
        return None
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
    from tools.image_generator_hunyuan_tencent_api import ImageGeneratorHunyuanTencentAPI
    from tools.image_generator_nanobanana_google_api import ImageGeneratorNanobananaGoogleAPI
    from tools.image_generator_doubao_seedream_volcengine_api import ImageGeneratorDoubaoSeedreamVolcengineAPI

    if provider == "tencent":
        return ImageGeneratorHunyuanTencentAPI()
    elif provider == "google":
        return ImageGeneratorNanobananaGoogleAPI(api_key=os.environ.get("GOOGLE_API_KEY", ""))
    elif provider == "volcengine":
        return ImageGeneratorDoubaoSeedreamVolcengineAPI()
    elif provider == "openai":
        return ImageGeneratorDoubaoSeedreamVolcengineAPI()
    else:
        return ImageGeneratorDoubaoSeedreamVolcengineAPI()


def _build_provider_video_generator(provider: str):
    """Build a video generator for the given provider, or fall back to volcengine."""
    from tools.video_generator_doubao_seedance_volcengine_api import VideoGeneratorDoubaoSeedanceVolcengineAPI
    from tools.video_generator_veo_google_api import VideoGeneratorVeoGoogleAPI

    if provider == "google":
        return VideoGeneratorVeoGoogleAPI(api_key=os.environ.get("GOOGLE_API_KEY", ""))
    else:
        return VideoGeneratorDoubaoSeedanceVolcengineAPI()


async def run_idea2video(task_id: str, req: Idea2VideoRequest):
    _, Idea2VideoPipeline = _import_pipelines()
    try:
        pipeline = Idea2VideoPipeline.init_from_config(config_path=req.config_path)
        # Use a deterministic cache key from input parameters so identical
        # inputs reuse the same cache directory and skip recomputation.
        cache_key_raw = "|".join([
            req.idea,
            req.user_requirement or "",
            req.style,
            str(req.episode_count),
            req.model_id,
            req.config_path,
        ])
        cache_key = hashlib.sha256(cache_key_raw.encode("utf-8")).hexdigest()[:16]
        pipeline.working_dir = os.path.join(pipeline.working_dir, cache_key)
        os.makedirs(pipeline.working_dir, exist_ok=True)

        # Override generators based on selected model's provider
        if req.model_id:
            model_info = _find_model_by_id(req.model_id)
            if model_info:
                provider = model_info["provider"]
                model_name = model_info["model"]
                from agents import Screenwriter, CharacterExtractor, CharacterPortraitsGenerator
                pipeline.chat_model = _build_provider_chat_model(provider, model_name)
                pipeline.image_generator = _build_provider_image_generator(provider)
                pipeline.video_generator = _build_provider_video_generator(provider)
                pipeline.screenwriter = Screenwriter(chat_model=pipeline.chat_model)
                pipeline.character_extractor = CharacterExtractor(chat_model=pipeline.chat_model)
                pipeline.character_portraits_generator = CharacterPortraitsGenerator(
                    image_generator=pipeline.image_generator)

        result_path = await pipeline(
            idea=req.idea,
            user_requirement=req.user_requirement,
            style=req.style,
            episode_count=req.episode_count,
        )
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", result_path, task_id),
            )
    except Exception as e:
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", str(e), task_id),
            )


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


# --- Static data for frontend ---
MODELS_DATA = {
    "creative_script": [
        {"id": "4", "name": "Doubao Pro", "provider": "volcengine", "model": "doubao-seed-2-0-lite-260428", "icon": "", "description": "ByteDance's large language model optimized for Chinese-language creative content."},
        {"id": "1", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hunyuan-turbos-latest", "icon": "", "description": "Tencent's powerful large language model with excellent Chinese creative writing and reasoning."},
        {"id": "2", "name": "Gemini 2.5 Pro", "provider": "openai", "model": "gemini-2.5-pro", "icon": "", "description": "Google's most capable model for complex reasoning, coding, and creative writing tasks."},
        {"id": "3", "name": "GPT-4o", "provider": "openai", "model": "gpt-4o", "icon": "", "description": "OpenAI's fast multimodal flagship model with strong creative writing capabilities."},
    ],
    "creative_episode": [],
    "creative_scenes": [
        {"id": "cs_1", "name": "Gemini 2.5 Flash", "provider": "openai", "model": "gemini-2.5-flash", "icon": "", "description": "Fast and efficient model for scene breakdown and structuring tasks."},
        {"id": "cs_2", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hunyuan-turbos-latest", "icon": "", "description": "Tencent's efficient model for scene structuring and plot development."},
    ],
    "creative_storyboards": [
        {"id": "sb_1", "name": "Gemini 2.5 Pro", "provider": "openai", "model": "gemini-2.5-pro", "icon": "", "description": "High-quality storyboard generation with detailed visual descriptions."},
        {"id": "sb_2", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hunyuan-turbos-latest", "icon": "", "description": "Tencent's model for storyboard layout and visual planning."},
    ],
    "drama_cover": [],
    "scene_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "ByteDance's high-quality image generation model for cinematic scene creation."},
        {"id": "2", "name": "Nanobanana (Google)", "provider": "google", "model": "nanobanana", "icon": "", "description": "Google's efficient image generation model with fast inference speeds."},
    ],
    "actor_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "High-quality character image generation with consistent facial features."},
        {"id": "2", "name": "Nanobanana (Google)", "provider": "google", "model": "nanobanana", "icon": "", "description": "Fast character portrait generation with good detail preservation."},
    ],
    "actor_three_view_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "Generate consistent three-view character reference sheets for animation."},
    ],
    "storyboard_image": [
        {"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0", "icon": "", "description": "High-quality storyboard frame generation with cinematic composition."},
        {"id": "2", "name": "Nanobanana (Google)", "provider": "google", "model": "nanobanana", "icon": "", "description": "Fast storyboard image generation for rapid prototyping."},
        {"id": "3", "name": "Hunyuan (Tencent)", "provider": "tencent", "model": "hy-image-v3.0", "icon": "", "description": "Tencent's powerful image generation model with strong text-to-image capabilities."},
    ],
    "character_look_costume": [],
    "actor_costume": [],
    "actor_costume_three_view": [],
    "prop_image": [],
    "prop_three_view_image": [],
    "storyboard_video": [
        {"id": "1", "name": "Seedance 1.5 Pro", "provider": "volcengine", "model": "seedance-1.5-pro", "icon": "", "description": "ByteDance's professional video generation model with smooth motion and high fidelity."},
        {"id": "2", "name": "Veo 3 (Google)", "provider": "google", "model": "veo-3", "icon": "", "description": "Google's state-of-the-art video generation model with exceptional quality and consistency."},
    ],
    "dialogue_voice": [],
    "storyboard_narration_voice": [],
    "storyboard_sfx_voice": [],
    "storyboard_music_voice": [],
    "creative_video": [
        {"id": "1", "name": "Seedance 1.5 Pro", "provider": "volcengine", "model": "seedance-1.5-pro", "icon": "", "description": "Professional video generation with flexible style control and high output quality."},
        {"id": "2", "name": "Veo 3 (Google)", "provider": "google", "model": "veo-3", "icon": "", "description": "Google's flagship video model, excelling at complex scenes and natural motion."},
    ],
}

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
    "web_name": "ViMax",
    "web_title": "ViMax - AI Video Generation",
    "copyright": "ViMax",
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
    asyncio.create_task(run_script2video(task_id, req))
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
    asyncio.create_task(run_idea2video(task_id, req))
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
    episode_sum: int = 20
    episode_duration: int = 60


@app.post("/app/shortplay/api/Index/submit")
async def legacy_submit(req: LegacySubmitRequest):
    """Handle creative mode submit from legacy frontend.
    Maps to idea2video or script2video based on req.script field.
    """
    task_id = str(uuid.uuid4())

    # Build user_requirement from optional fields
    user_requirement_parts = []
    if req.title:
        user_requirement_parts.append(f"Title: {req.title}")
    if req.description:
        user_requirement_parts.append(f"Description: {req.description}")
    if req.aspect_ratio:
        user_requirement_parts.append(f"Aspect ratio: {req.aspect_ratio}")
    if req.episode_duration:
        user_requirement_parts.append(f"Episode duration: {req.episode_duration}s")
    user_requirement = "; ".join(user_requirement_parts) if user_requirement_parts else ""

    if req.script in ("script", "drama"):
        # idea2video mode (creative from idea/prompt)
        idea_req = Idea2VideoRequest(
            idea=req.prompt,
            user_requirement=user_requirement,
            style=req.style or "Cinematic",
            config_path="configs/idea2video.yaml",
            model_id=req.model,
            episode_count=req.episode_sum,
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
                (task_id, "idea2video", "pending"),
            )
        asyncio.create_task(run_idea2video(task_id, idea_req))
    else:
        # Fallback: treat as idea2video
        idea_req = Idea2VideoRequest(
            idea=req.prompt,
            user_requirement=user_requirement,
            style=req.style or "Cinematic",
            config_path="configs/idea2video.yaml",
            model_id=req.model,
            episode_count=req.episode_sum,
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
                (task_id, "idea2video", "pending"),
            )
        asyncio.create_task(run_idea2video(task_id, idea_req))

    return success_response({"uuid": task_id, "task_id": task_id})


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

# --- Models ---
@app.get("/app/model/api/Model/models")
async def frontend_get_models():
    """Get available AI models grouped by scene type (frontend endpoint)."""
    return success_response(MODELS_DATA)


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
    import logging
    ref_path = None
    try:
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
        output_dir = os.path.join(".working_dir", "scenes")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"scene_{task_id}.png")
        result.save(output_path)

        logging.info(f"Scene image saved to {output_path}")

        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", output_path, task_id),
            )
    except Exception as e:
        import logging
        logging.exception(f"Scene image generation failed for task {task_id}")
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", str(e), task_id),
            )
    finally:
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
    import logging
    ref_paths = []
    try:
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

        output_dir = os.path.join(".working_dir", "storyboards")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"storyboard_{task_id}.png")
        result.save(output_path)

        logging.info(f"Storyboard image saved to {output_path}")

        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, result = ? WHERE task_id = ?",
                ("completed", output_path, task_id),
            )
    except Exception as e:
        logging.exception(f"Storyboard image generation failed for task {task_id}")
        with get_db() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error = ? WHERE task_id = ?",
                ("failed", str(e), task_id),
            )
    finally:
        for p in ref_paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


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
    asyncio.create_task(run_scene_image_generation(
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
    asyncio.create_task(run_storyboard_image_generation(
        task_id, prompt, req.model_id, req.first_image, req.last_image
    ))
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Generate/storyboardVideo")
async def generate_storyboard_video(req: GenerateStoryboardVideoRequest):
    """Generate a storyboard video. Returns a task_id for async processing."""
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "storyboard_video", "pending"),
        )
    # TODO: implement actual storyboard video generation pipeline
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Generate/characterLook")
async def generate_character_look(req: GenerateCharacterLookRequest):
    """Generate character look images. Returns a task_id for async processing."""
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "character_look", "pending"),
        )
    # TODO: implement actual character look generation pipeline
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Generate/dramaCover")
async def generate_drama_cover(req: GenerateDramaCoverRequest):
    """Generate a drama cover image. Returns a task_id for async processing."""
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "drama_cover", "pending"),
        )
    # TODO: implement actual drama cover generation pipeline
    return success_response({"task_id": task_id, "status": "pending"})


@app.post("/app/shortplay/api/Creative/video")
async def creative_video(req: CreativeVideoRequest):
    """Generate a video from image + prompt (creative mode). Returns a task_id."""
    task_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, mode, status) VALUES (?, ?, ?)",
            (task_id, "creative_video", "pending"),
        )
    # TODO: implement actual creative video generation (img2video)
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


# --- Upload (stub) ---
@app.post("/app/shortplay/api/Uploads/upload")
async def upload_file():
    """Upload a file (image/video/document). Stub - returns a placeholder URL."""
    # TODO: implement actual file upload handling
    return success_response({"url": "/uploads/placeholder.jpg", "dir_name": "uploads"})


# ===================================================================
# Frontend stub endpoints — 提供给前端的接口桩，返回写死的数据
# ===================================================================

CONTROL_CONFIG_DATA = {
    "web_name": "AIMovie",
    "web_title": "AIMovie - AI Video Generation",
    "web_logo": "",
    "web_icp": "",
    "web_mps": "",
    "web_mps_text": "",
    "copyright": "AIMovie",
    "version_name": "0.1.0",
    "version": 1,
    "wechat_group_qrcode_url": "",
    "guide_url": "",
    "project_background_video_url": "/aimovie/static/image/bg.mov",
    "login_background_image_url": "/aimovie/static/image/login-image.png",
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
    "showMenu": ["index", "square", "notice", "user"],
}


@app.get("/app/control/api/Public/config")
async def control_config():
    """前端控制面板配置."""
    return success_response(CONTROL_CONFIG_DATA)


@app.post("/app/control/api/Public/getSmsVcode")
async def get_sms_vcode():
    """获取短信验证码（桩）. 写死返回成功."""
    return success_response({"token": "stub-vcode-token-000000"})


# --- User ---
GUEST_USER_DATA = {
    "id": "guest-001",
    "nickname": "游客",
    "username": "guest",
    "mobile": "",
    "avatar": "",
    "token": "stub-guest-token-000000",
    "is_guest": True,
}


@app.get("/app/user/api/User/info")
async def user_info():
    """获取当前用户信息（桩）. 写死返回游客."""
    return success_response(GUEST_USER_DATA)


@app.post("/app/user/api/User/update")
async def user_update():
    """更新用户信息（桩）."""
    return success_response(GUEST_USER_DATA)


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
@app.post("/app/user/api/Login/loginPass")
@app.post("/app/user/api/Login/loginSms")
@app.post("/app/user/api/Login/wechatLogin")
@app.post("/app/user/api/Login/vcode")
async def login_stub():
    """登录接口（桩）. 写死返回游客用户."""
    return success_response(GUEST_USER_DATA)


@app.post("/app/user/api/Login/register")
async def register_stub():
    """注册接口（桩）."""
    return success_response(GUEST_USER_DATA)


@app.get("/app/user/api/Captcha/captcha_json")
async def captcha():
    """图形验证码（桩）."""
    return success_response({"captcha_id": "stub-captcha-001", "captcha_img": ""})


# --- Actor (桩) ---
@app.get("/app/shortplay/api/Actor/index")
async def actor_list():
    """演员列表（桩）."""
    return success_response({"data": [], "total": 0})


# --- Style (桩) ---
MOCK_STYLES = [
    {"id": "cinematic", "name": "Cinematic", "image": ""},
    {"id": "anime", "name": "Anime Style", "image": ""},
    {"id": "storybook", "name": "Storybook Illustration", "image": ""},
    {"id": "realistic", "name": "Photorealistic", "image": ""},
    {"id": "watercolor", "name": "Watercolor", "image": ""},
    {"id": "3d_render", "name": "3D Render", "image": ""},
    {"id": "pixel_art", "name": "Pixel Art", "image": ""},
    {"id": "comic", "name": "Comic Book", "image": ""},
]


@app.get("/app/shortplay/api/Style/index")
async def style_list():
    """风格列表（桩）."""
    return success_response({"data": MOCK_STYLES, "total": len(MOCK_STYLES)})


# --- Works / Drama / Episode (桩) ---
_EMPTY_LIST = {"data": [], "total": 0}


@app.get("/app/shortplay/api/Works/index")
async def works_list():
    return success_response(_EMPTY_LIST)


@app.get("/app/shortplay/api/Works/details")
async def works_details():
    return success_response({})


@app.get("/app/shortplay/api/Works/episode")
async def works_episode():
    return success_response(_EMPTY_LIST)


# --- Scene (桩) ---
@app.get("/app/shortplay/api/Scene/index")
async def scene_list():
    return success_response(_EMPTY_LIST)


# --- Storyboard (桩) ---
@app.get("/app/shortplay/api/Storyboard/index")
async def storyboard_list():
    return success_response(_EMPTY_LIST)


@app.get("/app/shortplay/api/StoryboardDialogue/index")
async def storyboard_dialogue_list():
    return success_response(_EMPTY_LIST)


# --- Prop (桩) ---
@app.get("/app/shortplay/api/Prop/index")
async def prop_list():
    return success_response(_EMPTY_LIST)


# --- CharacterLook (桩) ---
@app.get("/app/shortplay/api/CharacterLook/index")
async def character_look_list():
    return success_response(_EMPTY_LIST)


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
    """所有未显式定义的 /app/ 接口的通用桩."""
    return success_response(None)


# --- Startup ---
@app.on_event("startup")
async def startup():
    init_db()


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000)
