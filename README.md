# AIMovie - Agentic Video Generation

AI 驱动的智能视频生成平台，支持创意到视频、剧本到视频等多种工作流。

详细项目介绍请参阅 [backend/readme.md](backend/readme.md)。

## 界面展示

![主页面](doc/主页面.png)

![进度页面](doc/进度页面.png)

## 项目结构

```
AIMovie/
├── backend/          # Python FastAPI 后端
│   ├── main.py       # API 入口
│   ├── auth.py       # 账号密码登录
│   ├── tools/        # 图片/视频生成器 (Seedream, Nanobanana, Hunyuan 等)
│   ├── pipelines/    # 视频生成流水线
│   └── configs/      # YAML 配置文件
├── frontend/         # Vue 3 + Vite 前端
│   └── src/
├── start.sh          # Linux / macOS 一键启动
├── start.bat         # Windows 一键启动（双击运行）
├── start.ps1         # Windows 启动脚本（由 start.bat 调用）
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
cp backend/env_example backend/.env
```

编辑 `backend/.env`，填入你的 API Key：

```env
# 豆包/火山引擎
ARK_API_KEY=your_ark_api_key

# 腾讯混元
HUNYUAN_API_KEY=your_hunyuan_api_key

# GPUGEEK（可选）
GPUGEEK_API_KEY=your_gpugeek_api_key
```

### 3. 启动

**方式一：一键启动（推荐）**

| 系统 | 命令 |
|------|------|
| **Windows** | 双击 `start.bat`，或在项目根目录执行 `.\start.bat` |
| **Linux / macOS** | `./start.sh` |

Windows 脚本会依次完成：

1. `uv sync` 同步后端依赖
2. 启动后端并等待 `/health` 就绪
3. 首次运行自动 `npm install`，再启动前端

日志输出到项目根目录的 `backend.log`、`backend.err.log`。按 `Ctrl+C` 停止前后端。

**方式二：分别启动**

```bash
# 终端1 - 后端
cd backend && uv run python main.py

# 终端2 - 前端（Windows PowerShell 示例）
cd frontend
$env:VITE_REQUEST_BASE_URL="http://127.0.0.1:8666"
npm run dev
```

### 4. 访问

- 前端界面: http://localhost:36310/aimovie/
- 后端 API 文档: http://localhost:8666/docs
- 健康检查: http://localhost:8666/health

## 登录说明

当前仅支持**账号密码**注册与登录。首次使用请点击右上角「登录」→「注册」创建账号。

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
| POST | `/app/shortplay/api/Index/submit` | 前端提交生成任务 |
| POST | `/app/user/api/Login/register` | 账号注册 |
| POST | `/app/user/api/Login/login` | 账号登录 |
| GET  | `/api/tasks/{task_id}` | 查询任务状态 |
| GET  | `/api/tasks/{task_id}/stream` | 任务进度 SSE |
| GET  | `/api/models` | 获取模型列表 |
| GET  | `/api/styles` | 获取风格列表 |

## 更新

1. 一致性 [人物一致性](doc/同1个人物的背景由1个模型生成.png)
