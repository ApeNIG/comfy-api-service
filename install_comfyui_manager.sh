#!/bin/bash
# Install ComfyUI Manager - Extension manager for ComfyUI

echo "📦 Installing ComfyUI Manager..."
echo ""
echo "This adds a visual interface to:"
echo "  - Browse and install 1000+ custom nodes"
echo "  - Download models from HuggingFace"
echo "  - Manage your ComfyUI setup"
echo ""

cat << 'COMMANDS'
# Copy and paste these commands into your RunPod Web Terminal:

cd /workspace/ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
cd ComfyUI-Manager
pip install -r requirements.txt

# Restart ComfyUI to load the manager
pkill -f "python main.py"
cd /workspace/ComfyUI
nohup python main.py --listen 0.0.0.0 --port 8188 > /workspace/comfyui.log 2>&1 &

echo ""
echo "✅ ComfyUI Manager installed!"
echo ""
echo "To access it:"
echo "1. Wait 30 seconds for ComfyUI to restart"
echo "2. Open ComfyUI in your browser"
echo "3. Click the 'Manager' button (bottom right or in menu)"
echo ""
echo "What you can do with Manager:"
echo "  - Install ControlNet, AnimateDiff, IP-Adapter, etc."
echo "  - Download SDXL, SD 2.1, and custom models"
echo "  - Browse 1000+ community extensions"
echo "  - Update ComfyUI and extensions"
COMMANDS
