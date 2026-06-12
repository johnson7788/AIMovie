#!/usr/bin/env bash
# Expose AIMovie frontend (36310) via ngrok.
# Prerequisite: run ./start.sh first so backend + frontend are up.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
NGROK_CONFIG="$ROOT_DIR/ngrok.yml"
DEFAULT_NGROK_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/ngrok/ngrok.yml"
FRONTEND_URL="http://127.0.0.1:36310/aimovie/"
PID_FILE="$ROOT_DIR/.ngrok.pid"
LOG_FILE="$ROOT_DIR/ngrok.log"
NGROK_WEB_PORT="${NGROK_WEB_PORT:-4040}"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_step() {
    echo -e "${CYAN}[ngrok]${NC} $1"
}

log_error() {
    echo -e "${RED}[ngrok]${NC} $1" >&2
}

require_ngrok() {
    if ! command -v ngrok >/dev/null 2>&1; then
        log_error "ngrok not found. Install from https://ngrok.com/download and add to PATH."
        exit 1
    fi
}

ensure_authtoken() {
    if [[ -n "${NGROK_AUTHTOKEN:-}" ]]; then
        log_step "Configuring ngrok authtoken from NGROK_AUTHTOKEN..."
        ngrok config add-authtoken "$NGROK_AUTHTOKEN"
        return
    fi

    if [[ ! -f "$DEFAULT_NGROK_CONFIG" ]]; then
        log_error "ngrok authtoken not configured."
        cat <<EOF
Run once (token from https://dashboard.ngrok.com/get-started/your-authtoken):

  ngrok config add-authtoken <your_authtoken>

Or export NGROK_AUTHTOKEN before running this script.
EOF
        exit 1
    fi
}

check_frontend() {
    log_step "Checking frontend at $FRONTEND_URL ..."
    if ! curl -fsS --max-time 3 "$FRONTEND_URL" >/dev/null; then
        log_error "Frontend is not running on port 36310."
        cat <<EOF
Please start the app first:
  1. ./start.sh
  2. Wait until frontend is ready
  3. ./start-ngrok.sh start
EOF
        exit 1
    fi
}

ngrok_cmd() {
    ngrok start aimovie \
        --config "$DEFAULT_NGROK_CONFIG" \
        --config "$NGROK_CONFIG" \
        --log=stdout
}

is_running() {
    [[ -f "$PID_FILE" ]] || return 1
    local pid
    pid="$(cat "$PID_FILE")"
    kill -0 "$pid" 2>/dev/null
}

print_public_url() {
    local api_url="http://127.0.0.1:${NGROK_WEB_PORT}/api/tunnels"
    local public_url
    public_url="$(curl -fsS "$api_url" 2>/dev/null | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for tunnel in data.get("tunnels", []):
    if tunnel.get("proto") == "https":
        print(tunnel.get("public_url", ""))
        break
' || true)"
    if [[ -n "$public_url" ]]; then
        echo -e "${GREEN}[ngrok]${NC} Public URL: ${public_url%/}/aimovie/"
    else
        echo -e "${YELLOW}[ngrok]${NC} Tunnel is starting. Check ${api_url} or ${LOG_FILE}."
    fi
}

start_foreground() {
    require_ngrok
    ensure_authtoken
    check_frontend

    log_step "Starting ngrok tunnel (frontend 36310 -> public HTTPS)..."
    log_step "Share this URL with others (include /aimovie/ path):"
    echo -e "${GREEN}  https://<your-subdomain>.ngrok-free.app/aimovie/${NC}"
    echo ""
    log_step "Press Ctrl+C to stop ngrok (start.sh keeps running separately)."
    echo ""

    ngrok_cmd
}

start_background() {
    require_ngrok
    ensure_authtoken
    check_frontend

    if is_running; then
        log_step "ngrok is already running (PID=$(cat "$PID_FILE"))."
        print_public_url
        exit 0
    fi

    log_step "Starting ngrok in background..."
    nohup ngrok start aimovie \
        --config "$DEFAULT_NGROK_CONFIG" \
        --config "$NGROK_CONFIG" \
        --log=stdout >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    sleep 2

    if ! is_running; then
        log_error "Failed to start ngrok. Last log lines:"
        tail -n 20 "$LOG_FILE" || true
        rm -f "$PID_FILE"
        exit 1
    fi

    log_step "ngrok started (PID=$(cat "$PID_FILE"))."
    log_step "Log file: $LOG_FILE"
    print_public_url
    log_step "Stop with: ./start-ngrok.sh stop"
}

stop_background() {
    if ! is_running; then
        log_step "ngrok is not running."
        rm -f "$PID_FILE"
        exit 0
    fi

    local pid
    pid="$(cat "$PID_FILE")"
    log_step "Stopping ngrok (PID=$pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    log_step "ngrok stopped."
}

show_status() {
    if is_running; then
        log_step "ngrok is running (PID=$(cat "$PID_FILE"))."
        print_public_url
        log_step "Log file: $LOG_FILE"
    else
        log_step "ngrok is not running."
        rm -f "$PID_FILE"
        exit 1
    fi
}

show_logs() {
    if [[ ! -f "$LOG_FILE" ]]; then
        log_step "No log file yet: $LOG_FILE"
        exit 0
    fi
    tail -f "$LOG_FILE"
}

usage() {
    cat <<EOF
Usage:
  ./start-ngrok.sh              Run ngrok in foreground
  ./start-ngrok.sh start        Run ngrok in background (recommended on Linux)
  ./start-ngrok.sh stop         Stop background ngrok
  ./start-ngrok.sh status       Show running state and public URL
  ./start-ngrok.sh logs         Tail ngrok log file

Prerequisite: ./start.sh must be running first.
EOF
}

case "${1:-}" in
    ""|run|foreground)
        start_foreground
        ;;
    start|daemon|bg|background)
        start_background
        ;;
    stop)
        stop_background
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        log_error "Unknown command: $1"
        usage
        exit 1
        ;;
esac
