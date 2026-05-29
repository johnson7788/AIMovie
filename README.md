# ViMax - Agentic Video Generation

AI 驱动的智能视频生成平台，支持创意到视频、剧本到视频等多种工作流。

详细项目介绍请参阅 [backend/readme.md](backend/readme.md)。

## 项目结构

```
AIMovie/
├── backend/          # Python FastAPI 后端
│   ├── main.py       # API 入口
│   ├── tools/        # 图片/视频生成器 (Seedream, Nanobanana, Hunyuan 等)
│   ├── pipelines/    # 视频生成流水线
│   └── configs/      # YAML 配置文件
├── frontend/         # Vue 3 + Vite 前端
│   └── src/
├── start.sh          # 一键启动脚本
└── README.md
```

## 环境要求

- **Python** >= 3.12
- **Node.js** >= 18
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (Python 包管理)

## 快速开始

### 1. 安装依赖

```bash
# 后端
cd backend
uv sync

# 前端
cd ../frontend
npm install
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入你的 API Key：

```env
# 豆包/火山引擎
ARK_API_KEY=your_ark_api_key

# 腾讯混元
HUNYUAN_API_KEY=your_hunyuan_api_key
```

### 3. 启动

**方式一：一键启动（推荐）**

```bash
./start.sh
```

自动启动前端 (port 36310) 和后端 (port 8000)，按 `Ctrl+C` 停止。

**方式二：分别启动**

```bash
# 终端1 - 后端
cd backend && uv run python main.py

# 终端2 - 前端
cd frontend && npm run dev
```

### 4. 访问

- 前端界面: http://localhost:36310
- 后端 API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 支持的 AI 模型

### 图片生成
| 模型 | Provider | 说明 |
|------|----------|------|
| Seedream 4.0 | 火山引擎 | 豆包文生图 |
| Nanobanana | Google | Gemini 图片生成 |
| Hunyuan | 腾讯混元 | hy-image-v3.0 |

### 视频生成
| 模型 | Provider | 说明 |
|------|----------|------|
| Seedance 1.5 Pro | 火山引擎 | 图生视频 |
| Veo 3 | Google | 视频生成 |

## API 端点 (核心)

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/script2video` | 剧本→视频 |
| POST | `/api/idea2video` | 创意→视频 |
| POST | `/app/shortplay/api/Generate/sceneImage` | 场景图生成 |
| POST | `/app/shortplay/api/Generate/storyboardImage` | 分镜图生成 |
| GET  | `/api/tasks/{task_id}` | 查询任务状态 |
| GET  | `/api/models` | 获取模型列表 |
| GET  | `/api/styles` | 获取风格列表 |
