#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Colors for log prefix
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cleanup() {
    echo ""
    echo -e "${GREEN}[start.sh]${NC} 收到中断信号，正在停止前后端服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}[start.sh]${NC} 前后端已停止。"
    exit 0
}

trap cleanup SIGINT SIGTERM

# --- Start Backend ---
echo -e "${GREEN}[start.sh]${NC} 启动后端 (backend/main.py) ..."
cd "$BACKEND_DIR"
uv run python main.py 2>&1 | while IFS= read -r line; do
    echo -e "${BLUE}[backend]${NC} $line"
done &
BACKEND_PID=$!

# --- Start Frontend ---
echo -e "${GREEN}[start.sh]${NC} 启动前端 (vite dev) ..."
cd "$FRONTEND_DIR"
npm run dev 2>&1 | while IFS= read -r line; do
    echo -e "${GREEN}[frontend]${NC} $line"
done &
FRONTEND_PID=$!

echo -e "${GREEN}[start.sh]${NC} 前后端已启动 (backend PID=$BACKEND_PID, frontend PID=$FRONTEND_PID)"
echo -e "${GREEN}[start.sh]${NC} 按 Ctrl+C 停止所有服务"

wait
