#!/usr/bin/env bash
set -euo pipefail

mkdir -p /workspaces/comfy-data

# ComfyUI on 8188
if ! ss -ltn sport = :8188 | grep -q 8188; then
  cd /workspaces/ComfyUI
  test -d .venv || python3 -m venv .venv
  . .venv/bin/activate
  pip -q install --upgrade pip
  pip -q install -r requirements.txt
  nohup python main.py --cpu --listen 0.0.0.0 --port 8188 \
    > /workspaces/comfy-data/comfy.log 2>&1 &
fi

# FastAPI on 8000
export PATH="$HOME/.local/bin:$PATH"
if ! ss -ltn sport = :8000 | grep -q 8000; then
  cd /workspaces/comfy-api-service
  python3 -m pip install --user poetry >/dev/null 2>&1 || true
  poetry install --no-root
  nohup poetry run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 \
    > /workspaces/comfy-data/api.log 2>&1 &
fi
