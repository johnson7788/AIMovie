#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/logs"
BACKEND_PORT="${SERVER_PORT:-8666}"
BACKEND_BASE_URL="http://127.0.0.1:${BACKEND_PORT}"
HEALTH_URL="${BACKEND_BASE_URL}/health"
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
BACKEND_LOG="$LOG_DIR/backend-$RUN_STAMP.log"
FRONTEND_LOG="$LOG_DIR/frontend-$RUN_STAMP.log"

BACKEND_PID=""
FRONTEND_PID=""
STARTED_BACKEND=0
STARTED_FRONTEND=0

# Colors for log prefix
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_step() {
    echo -e "${GREEN}[start.sh]${NC} $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

backend_ready() {
    curl -fsS "$HEALTH_URL" >/dev/null 2>&1
}

cleanup() {
    echo ""
    log_step "收到中断信号，正在停止本次脚本启动的服务..."
    if [ "$STARTED_FRONTEND" -eq 1 ] && [ -n "${FRONTEND_PID:-}" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi
    if [ "$STARTED_BACKEND" -eq 1 ] && [ -n "${BACKEND_PID:-}" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    log_step "已停止。"
    exit 0
}

trap cleanup SIGINT SIGTERM

for cmd in uv node npm curl; do
    if ! command_exists "$cmd"; then
        echo "Error: '$cmd' not found. Please install it and add it to PATH." >&2
        exit 1
    fi
done

mkdir -p "$LOG_DIR"

# --- Start Backend ---
log_step "同步后端依赖 (uv sync) ..."
cd "$BACKEND_DIR"
uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple
log_step "校验后端运行时依赖 (ffmpeg / last-frame) ..."
uv run python -c "from utils.video import _resolve_ffmpeg_exe; p=_resolve_ffmpeg_exe(); print('ffmpeg:', p); import os; assert os.path.isfile(p)"
export PYTHONUTF8=1

if backend_ready; then
    log_step "后端已在端口 $BACKEND_PORT 运行，复用现有后端。"
else
    log_step "启动后端 (backend/main.py) ..."
    log_step "后端日志: $BACKEND_LOG"
    uv run python main.py >"$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    STARTED_BACKEND=1
fi

# --- Wait for backend to be ready ---
log_step "等待后端就绪 ($HEALTH_URL) ..."
for i in $(seq 1 60); do
    if backend_ready; then
        log_step "后端已就绪。"
        break
    fi
    if [ "$STARTED_BACKEND" -eq 1 ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "后端进程提前退出。最近日志：" >&2
        tail -n 60 "$BACKEND_LOG" 2>/dev/null || true
        exit 1
    fi
    if [ $i -eq 60 ]; then
        echo "后端启动超时，请检查日志：$BACKEND_LOG" >&2
        exit 1
    fi
    sleep 2
done

# --- Start Frontend ---
log_step "启动前端 (vite dev) ..."
cd "$FRONTEND_DIR"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log_step "首次运行，安装前端依赖 (npm install) ..."
    npm install
fi
export VITE_REQUEST_BASE_URL="$BACKEND_BASE_URL"
log_step "前端代理目标: $VITE_REQUEST_BASE_URL"
log_step "前端日志: $FRONTEND_LOG"
npm run dev >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
STARTED_FRONTEND=1

log_step "前后端已启动 (backend PID=${BACKEND_PID:-existing}, frontend PID=$FRONTEND_PID)"
log_step "Frontend URL: http://127.0.0.1:36310/aimovie/"
log_step "按 Ctrl+C 停止本次脚本启动的服务"

wait "$FRONTEND_PID"
