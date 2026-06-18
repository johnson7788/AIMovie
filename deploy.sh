#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[deploy]${NC} $1"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $1"; }

# --- Pre-flight checks ---
if ! command -v docker >/dev/null 2>&1; then
    echo "Error: 'docker' not found. Please install Docker first." >&2
    exit 1
fi

if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "Error: docker compose plugin not found." >&2
    exit 1
fi

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
    warn "backend/.env 不存在，从 env_example 复制一份（请填写 API Key）"
    cp "$ROOT_DIR/backend/env_example" "$ROOT_DIR/backend/.env"
fi

# --- Build & start ---
log "构建并启动容器 ..."
$COMPOSE up --build -d

# --- Print info ---
echo ""
log "服务已启动："
$COMPOSE ps
echo ""
log "前端地址: http://localhost:8080/aimovie/"
log "后端地址: http://localhost:8666 (健康检查: /health)"
echo ""
log "查看日志: $COMPOSE logs -f"
log "停止服务: $COMPOSE down"
