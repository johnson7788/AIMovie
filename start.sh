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
uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple
export PYTHONUTF8=1
uv run python main.py 2>&1 | while IFS= read -r line; do
    echo -e "${BLUE}[backend]${NC} $line"
done &
BACKEND_PID=$!

# --- Wait for backend to be ready ---
BACKEND_URL="${VITE_REQUEST_BASE_URL:-http://127.0.0.1:8666}"
echo -e "${GREEN}[start.sh]${NC} 等待后端就绪 ($BACKEND_URL) ..."
for i in $(seq 1 60); do
    if curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL" 2>/dev/null | grep -q "200\|404\|405"; then
        echo -e "${GREEN}[start.sh]${NC} 后端已就绪。"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${GREEN}[start.sh]${NC} 后端启动超时，请检查。"
    fi
    sleep 1
done

# --- Start Frontend ---
echo -e "${GREEN}[start.sh]${NC} 启动前端 (vite dev) ..."
cd "$FRONTEND_DIR"
export VITE_REQUEST_BASE_URL="$BACKEND_URL"
npm run dev 2>&1 | while IFS= read -r line; do
    echo -e "${GREEN}[frontend]${NC} $line"
done &
FRONTEND_PID=$!

echo -e "${GREEN}[start.sh]${NC} 前后端已启动 (backend PID=$BACKEND_PID, frontend PID=$FRONTEND_PID)"
echo -e "${GREEN}[start.sh]${NC} 按 Ctrl+C 停止所有服务"

wait
