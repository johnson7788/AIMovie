# ViMax API Documentation

ViMax (Agentic Video Generation) 提供基于 HTTP 的 REST API，支持两种视频生成模式：

- **Script2Video**: 从剧本/脚本生成视频
- **Idea2Video**: 从创意/想法生成视频

## 启动服务

```bash
cd backend
pip install fastapi uvicorn
python main.py
```

服务默认监听 `http://0.0.0.0:8000`。

交互式 API 文档：`http://localhost:8000/docs`

## 响应格式

所有 API 响应遵循统一信封格式：

```json
{
  "code": 200,
  "data": { ... },
  "msg": "success"
}
```

- `code`: 状态码，`200` 表示成功
- `data`: 响应数据 payload
- `msg`: 消息文本（错误时包含错误描述）

---

## 接口总览

### 核心 Pipeline 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/script2video` | 提交剧本生成视频任务 |
| POST | `/api/idea2video` | 提交创意生成视频任务 |
| GET | `/api/tasks/{task_id}` | 查询任务状态 |
| GET | `/api/tasks` | 列出所有任务 |

### 前端配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/models` | 获取可用 AI 模型列表（按场景分组） |
| GET | `/api/styles` | 获取可用视觉风格列表 |
| GET | `/api/config` | 获取站点配置 |

### 前端业务接口（兼容前端 $http 调用路径）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/app/model/api/Model/models` | 获取 AI 模型列表（同 `/api/models`） |
| GET | `/app/model/api/Task/index` | 查询任务列表（支持分页/过滤） |
| GET | `/app/model/api/Voice/modelList` | 获取语音模型列表 |
| GET | `/app/shortplay/api/Voice/list` | 获取语音列表 |
| POST | `/app/shortplay/api/Generate/sceneImage` | 生成场景图片 |
| POST | `/app/shortplay/api/Generate/storyboardImage` | 生成 storyboard 图片 |
| POST | `/app/shortplay/api/Generate/storyboardVideo` | 生成 storyboard 视频 |
| POST | `/app/shortplay/api/Generate/characterLook` | 生成角色外观图片 |
| POST | `/app/shortplay/api/Generate/dramaCover` | 生成短剧封面 |
| POST | `/app/shortplay/api/Creative/video` | 图生视频（创意模式） |
| POST | `/app/shortplay/api/Uploads/upload` | 文件上传（stub） |

---

## 接口详情

### GET /health

健康检查。

**Response:**

```json
{
  "status": "ok"
}
```

---

### POST /api/script2video

提交一个剧本转视频的异步任务。Pipeline 会从剧本中提取角色、生成角色肖像、设计分镜、生成帧图片、组装视频。

**Request Body:**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `script` | string | 是 | - | 剧本/脚本文本 |
| `user_requirement` | string | 否 | `""` | 用户对视频的要求（如镜头数量限制） |
| `style` | string | 否 | `"Cinematic"` | 视觉风格 |
| `config_path` | string | 否 | `"configs/script2video.yaml"` | Pipeline 配置文件路径 |

**Request Example:**

```json
{
  "script": "EXT. SCHOOL GYM - DAY\nA group of students are practicing basketball...",
  "user_requirement": "Fast-paced with no more than 15 shots.",
  "style": "Anime Style",
  "config_path": "configs/script2video.yaml"
}
```

**Response:**

```json
{
  "code": 200,
  "data": {
    "task_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "mode": "script2video",
    "status": "pending",
    "result": null,
    "error": null
  },
  "msg": "success"
}
```

---

### POST /api/idea2video

提交一个创意转视频的异步任务。Pipeline 会先将创意发展为故事，提取角色并生成肖像，再为每个场景生成视频，最后拼接。

**Request Body:**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `idea` | string | 是 | - | 创意/想法描述 |
| `user_requirement` | string | 否 | `""` | 用户对视频的要求（如场景数量限制） |
| `style` | string | 否 | `"Cinematic"` | 视觉风格 |
| `config_path` | string | 否 | `"configs/idea2video.yaml"` | Pipeline 配置文件路径 |

**Request Example:**

```json
{
  "idea": "A curious orange tabby cat explores a cozy old bookshop...",
  "user_requirement": "Do not exceed 3 scenes. Each scene should be no more than 5 shots.",
  "style": "Warm, storybook illustration style",
  "config_path": "configs/idea2video.yaml"
}
```

**Response:**

```json
{
  "code": 200,
  "data": {
    "task_id": "a1b2c3d4-5678-9012-abcd-ef0123456789",
    "mode": "idea2video",
    "status": "pending",
    "result": null,
    "error": null
  },
  "msg": "success"
}
```

---

### GET /api/tasks/{task_id}

查询指定任务的状态和结果。

**Path Parameters:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `task_id` | string | 任务 ID（由提交接口返回） |

**Response:**

```json
{
  "code": 200,
  "data": {
    "task_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "mode": "script2video",
    "status": "completed",
    "result": ".working_dir/script2video/final_video.mp4",
    "error": null
  },
  "msg": "success"
}
```

**404 响应:**

```json
{
  "detail": "Task not found"
}
```

---

### GET /api/tasks

列出所有任务。

**Response:** 任务列表，按创建时间倒序排列。

---

### GET /api/models

获取可用 AI 模型列表，按场景类型分组。

**Response:**

```json
{
  "code": 200,
  "data": {
    "creative_script": [{"id": "1", "name": "Gemini 2.5 Pro", "provider": "openai", "model": "gemini-2.5-pro"}],
    "creative_scenes": [{"id": "1", "name": "Gemini 2.5 Flash", "provider": "openai", "model": "gemini-2.5-flash"}],
    "scene_image": [{"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0"}],
    "storyboard_image": [{"id": "1", "name": "Seedream 4.0", "provider": "volcengine", "model": "seedream-4.0"}],
    "storyboard_video": [{"id": "1", "name": "Seedance 1.5 Pro", "provider": "volcengine", "model": "seedance-1.5-pro"}],
    "creative_video": [{"id": "1", "name": "Seedance 1.5 Pro", "provider": "volcengine", "model": "seedance-1.5-pro"}],
    "actor_image": [...],
    "actor_three_view_image": [...],
    ...
  },
  "msg": "success"
}
```

---

### GET /api/styles

获取可用视觉风格列表。

**Response:**

```json
{
  "code": 200,
  "data": [
    {"id": "cinematic", "name": "Cinematic"},
    {"id": "anime", "name": "Anime Style"},
    {"id": "storybook", "name": "Storybook Illustration"},
    {"id": "realistic", "name": "Photorealistic"},
    {"id": "watercolor", "name": "Watercolor"},
    {"id": "3d_render", "name": "3D Render"},
    {"id": "pixel_art", "name": "Pixel Art"},
    {"id": "comic", "name": "Comic Book"}
  ],
  "msg": "success"
}
```

---

### GET /api/config

获取站点配置。

**Response:**

```json
{
  "code": 200,
  "data": {
    "web_name": "ViMax",
    "web_title": "ViMax - AI Video Generation",
    "copyright": "ViMax",
    "version_name": "0.1.0",
    "version": 1
  },
  "msg": "success"
}
```

---

### GET /app/model/api/Model/models

前端兼容接口，等同于 `/api/models`。

---

### GET /app/model/api/Task/index

查询任务列表（支持分页和过滤）。

**Query Parameters:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `scene` | string | 否 | - | 按任务模式过滤（如 `script2video`） |
| `drama_id` | string | 否 | - | 按作品 ID 过滤 |
| `limit` | int | 否 | `20` | 每页数量 |
| `page` | int | 否 | `1` | 页码 |

**Response:**

```json
{
  "code": 200,
  "data": {
    "data": [
      {
        "task_id": "xxx",
        "mode": "script2video",
        "status": "completed",
        "result": "/path/to/video.mp4",
        "error": null,
        "created_at": "2026-05-21 11:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  },
  "msg": "success"
}
```

---

### GET /app/model/api/Voice/modelList

获取语音模型列表。

**Response:**

```json
{
  "code": 200,
  "data": [
    {"id": "1", "name": "Female - Warm", "language": "zh-CN", "gender": "female", "age": "adult"},
    {"id": "2", "name": "Male - Deep", "language": "zh-CN", "gender": "male", "age": "adult"}
  ],
  "msg": "success"
}
```

---

### GET /app/shortplay/api/Voice/list

获取语音列表。

**Response:**

```json
{
  "code": 200,
  "data": {
    "data": [...],
    "total": 4
  },
  "msg": "success"
}
```

---

### POST /app/shortplay/api/Generate/sceneImage

生成场景图片。

**Request Body:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drama_id` | string | 否 | 作品 ID |
| `episode_id` | string | 否 | 剧集 ID |
| `scene_id` | string | 否 | 场景 ID |
| `name` | string | 否 | 场景名称 |
| `description` | string | 否 | 场景描述 |
| `prompt` | string | 否 | 图片生成提示词 |
| `model_id` | string | 否 | 使用的模型 ID |
| `image_url` | string | 否 | 参考图片 URL |

**Response:**

```json
{
  "code": 200,
  "data": {
    "task_id": "xxx",
    "status": "pending"
  },
  "msg": "success"
}
```

---

### POST /app/shortplay/api/Generate/storyboardImage

生成 storyboard 图片。

**Request Body:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drama_id` | string | 否 | 作品 ID |
| `episode_id` | string | 否 | 剧集 ID |
| `storyboard_id` | string | 否 | Storyboard ID |
| `prompt` | string | 否 | 图片生成提示词 |
| `model_id` | string | 否 | 使用的模型 ID |
| `first_image` | string | 否 | 首帧图片 URL |
| `last_image` | string | 否 | 尾帧图片 URL |

**Response:** 返回 `task_id`。

---

### POST /app/shortplay/api/Generate/storyboardVideo

生成 storyboard 视频。

**Request Body:**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `drama_id` | string | 否 | - | 作品 ID |
| `episode_id` | string | 否 | - | 剧集 ID |
| `storyboard_id` | string | 否 | - | Storyboard ID |
| `prompt` | string | 否 | - | 视频生成提示词 |
| `negative_prompt` | string | 否 | - | 反向提示词 |
| `first_image` | string | 否 | - | 首帧图片 URL |
| `last_image` | string | 否 | - | 尾帧图片 URL |
| `duration` | int | 否 | `5` | 视频时长（秒） |
| `model_id` | string | 否 | - | 使用的模型 ID |

**Response:** 返回 `task_id`。

---

### POST /app/shortplay/api/Generate/characterLook

生成角色外观图片。

**Request Body:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `actor_id` | string | 否 | 角色 ID |
| `drama_id` | string | 否 | 作品 ID |
| `prompt` | string | 否 | 提示词 |
| `model_id` | string | 否 | 模型 ID |

**Response:** 返回 `task_id`。

---

### POST /app/shortplay/api/Generate/dramaCover

生成短剧封面。

**Request Body:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `drama_id` | string | 否 | 作品 ID |
| `prompt` | string | 否 | 提示词 |
| `model_id` | string | 否 | 模型 ID |

**Response:** 返回 `task_id`。

---

### POST /app/shortplay/api/Creative/video

图生视频（创意模式）。根据参考图片和提示词生成视频。

**Request Body:**

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image_url` | string | 是 | - | 参考图片 URL |
| `prompt` | string | 否 | `""` | 视频生成提示词 |
| `duration` | int | 否 | `5` | 视频时长（秒） |
| `resolution` | string | 否 | `"1080p"` | 分辨率 |
| `model_id` | string | 否 | - | 使用的模型 ID |

**Response:**

```json
{
  "code": 200,
  "data": {
    "task_id": "xxx",
    "status": "pending"
  },
  "msg": "success"
}
```

---

### POST /app/shortplay/api/Uploads/upload

文件上传接口（当前为 stub，返回占位 URL）。

**TODO:** 实现实际文件上传处理。

---

## 任务状态流转

```
pending → running → completed
                  → failed
```

- **pending**: 任务已提交，等待执行
- **running**: 任务正在执行（内部状态，通过异步方式处理）
- **completed**: 任务完成，`result` 字段包含视频文件路径
- **failed**: 任务失败，`error` 字段包含错误信息

---

## 数据存储

任务信息持久化在 SQLite 数据库 `tasks.db` 中，服务重启后任务信息不会丢失。

---

## 配置文件

Pipeline 通过 YAML 配置文件指定使用的 LLM、图片生成器和视频生成器。默认配置：

| 模式 | 默认配置 | 说明 |
|------|----------|------|
| script2video | `configs/script2video.yaml` | Google Gemini + Google Image/Video API |
| idea2video | `configs/idea2video.yaml` | 火山引擎 Doubao + Seedream/Seedance |

可选配置文件：

| 文件 | 说明 |
|------|------|
| `configs/script2video_minimax.yaml` | 使用 MiniMax 提供商 |
| `configs/script2video_volcengine.yaml` | 使用火山引擎提供商 |
| `configs/idea2video_minimax.yaml` | 使用 MiniMax 提供商 |

---

## 注意事项

1. 视频生成是耗时操作（通常数分钟到数十分钟），请通过轮询 `/api/tasks/{task_id}` 或 `/app/model/api/Task/index` 获取进度
2. API Key 通过环境变量加载（`.env` 文件），确保相关 API Key 已配置
3. 生成结果保存在 `working_dir` 配置的目录下，Pipeline 支持断点续跑（跳过已存在的中间文件）
4. 任务持久化在 SQLite 数据库中（`tasks.db`），服务重启后任务信息保留
5. 生成类接口（`/app/shortplay/api/Generate/*`、`/app/shortplay/api/Creative/video`）当前返回任务 ID，实际 pipeline 对接待实现（代码中标记为 TODO）
