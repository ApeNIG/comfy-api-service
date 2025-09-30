#!/usr/bin/env bash
set -Eeuo pipefail

LOG_DIR="/workspaces/comfy-data"
COMFY_ROOT="/workspaces/ComfyUI"
API_ROOT="/workspaces/comfy-api-service"

mkdir -p "$LOG_DIR"

# --- ComfyUI (8188) ---
if ! ss -lnt | grep -q ':8188'; then
  cd "$COMFY_ROOT"
  test -d .venv || python3 -m venv .venv
  . .venv/bin/activate
  pip install -r requirements.txt
  nohup python3 main.py --cpu --listen 0.0.0.0 --port 8188 > "$LOG_DIR/comfy.log" 2>&1 &
fi

# --- FastAPI (8000) ---
if ! ss -lnt | grep -q ':8000'; then
  cd "$API_ROOT"
  export PATH="$HOME/.local/bin:$PATH"
  poetry install --no-root
  nohup poetry run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/api.log" 2>&1 &
fi
