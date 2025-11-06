#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/workspaces/ComfyUI"
DATA_DIR="/workspaces/comfy-data"

command -v git >/dev/null 2>&1 || { sudo apt-get update && sudo apt-get install -y git; }

[ -d "$APP_DIR" ] || git clone https://github.com/comfyanonymous/ComfyUI.git "$APP_DIR"
cd "$APP_DIR"

python3 -m venv .venv
. .venv/bin/activate
pip install -U pip wheel
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

mkdir -p "$DATA_DIR"/{models,output,input}
for d in models output input; do
  [ -L "$APP_DIR/$d" ] || { rm -rf "$APP_DIR/$d" 2>/dev/null || true; ln -s "$DATA_DIR/$d" "$APP_DIR/$d"; }
done
