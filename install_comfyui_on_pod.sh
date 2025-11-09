#!/bin/bash
# Install ComfyUI on the running RunPod pod via SSH

POD_ID="jfmkqw45px5o3x"

echo "📦 Installing ComfyUI on pod $POD_ID..."
echo ""
echo "This will take a few minutes. The installation includes:"
echo "  - Cloning ComfyUI repository"
echo "  - Installing Python dependencies"
echo "  - Downloading Stable Diffusion 1.5 model"
echo "  - Starting ComfyUI server on port 8188"
echo ""

# Create installation script
cat > /tmp/install_comfyui.sh << 'INSTALL_SCRIPT'
#!/bin/bash
set -e

echo "=== Installing ComfyUI ==="

# Navigate to workspace
cd /workspace

# Clone ComfyUI if not already present
if [ ! -d "ComfyUI" ]; then
    echo "Cloning ComfyUI..."
    git clone https://github.com/comfyanonymous/ComfyUI.git
fi

cd ComfyUI

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Download SD 1.5 model if not present
MODEL_DIR="models/checkpoints"
mkdir -p $MODEL_DIR

if [ ! -f "$MODEL_DIR/v1-5-pruned-emaonly.ckpt" ]; then
    echo "Downloading Stable Diffusion 1.5 model..."
    wget -q --show-progress -O "$MODEL_DIR/v1-5-pruned-emaonly.ckpt" \
        "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt"
fi

# Create startup script
cat > /workspace/start_comfyui.sh << 'STARTUP'
#!/bin/bash
cd /workspace/ComfyUI
python main.py --listen 0.0.0.0 --port 8188
STARTUP

chmod +x /workspace/start_comfyui.sh

# Start ComfyUI in background
echo "Starting ComfyUI server..."
nohup /workspace/start_comfyui.sh > /workspace/comfyui.log 2>&1 &

echo "=== Installation Complete! ==="
echo "ComfyUI is starting on port 8188"
echo "Check logs: tail -f /workspace/comfyui.log"
INSTALL_SCRIPT

echo "📝 Installation script created"
echo ""
echo "⚠️  MANUAL STEPS NEEDED:"
echo ""
echo "1. In the RunPod Connect tab, click 'Open Web Terminal'"
echo "2. In the terminal, run these commands:"
echo ""
echo "   cd /workspace"
echo "   wget https://raw.githubusercontent.com/comfyanonymous/ComfyUI/master/requirements.txt -O /tmp/req.txt 2>/dev/null || true"
echo "   git clone https://github.com/comfyanonymous/ComfyUI.git"
echo "   cd ComfyUI"
echo "   pip install -r requirements.txt"
echo "   mkdir -p models/checkpoints"
echo "   wget -O models/checkpoints/v1-5-pruned-emaonly.ckpt https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt"
echo "   python main.py --listen 0.0.0.0 --port 8188 &"
echo ""
echo "3. Wait 2-3 minutes for the model to download and ComfyUI to start"
echo "4. Check if port 8188 shows 'Ready' in the Connect tab"
echo ""

rm /tmp/install_comfyui.sh
