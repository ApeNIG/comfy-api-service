# Using Creator to Generate Its Own Design Assets

## 🎯 The Concept

Use the Creator platform's ComfyUI integration to generate unique design assets for the platform itself. This demonstrates the product's capabilities while creating custom, brand-aligned visuals.

## ✅ What You've Built

I've set up a complete workflow for generating hero images and background assets:

1. **Generation Script**: [scripts/generate_hero_images.py](scripts/generate_hero_images.py)
2. **Asset Directory**: `assets/generated/` with subdirectories for different asset types
3. **Brand-Aligned Prompts**: 5 carefully crafted prompts matching your coral/dark theme
4. **ComfyUI Integration**: Uses your existing ComfyUI client

## 🚀 How to Run

### Prerequisites

You need a ComfyUI instance running. Choose one option:

**Option 1: Local ComfyUI**
```bash
# Install ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Download a model (e.g., Stable Diffusion 1.5)
# Place in ComfyUI/models/checkpoints/

# Start server
python main.py --listen 0.0.0.0 --port 8188

# Update .env
echo "COMFYUI_URL=http://localhost:8188" >> .env
```

**Option 2: RunPod GPU Instance**
```bash
# 1. Create RunPod account and start a GPU pod
# 2. Select a template with ComfyUI pre-installed, or:
#    - Use "RunPod Pytorch" template
#    - Clone ComfyUI in the pod's terminal
#    - Start with: python main.py --listen 0.0.0.0 --port 8188

# 3. Get the proxy URL (e.g., https://xxxxx-8188.proxy.runpod.net)
# 4. Update .env:
echo "COMFYUI_URL=https://your-runpod-url-8188.proxy.runpod.net" >> .env
```

**Option 3: Other Cloud/Self-Hosted**
Any ComfyUI instance works - just update `COMFYUI_URL` in `.env`

### Test Connection

```bash
python scripts/test_comfyui_connection.py
```

If you see ✅, you're ready to generate!

### Generate Images

```bash
# From project root
python scripts/generate_hero_images.py
```

This will:
1. Check if ComfyUI is running
2. Generate 9 hero images with professional SaaS-style prompts
3. Save them to `assets/generated/heroes/`
4. Each image takes ~2-3 minutes (total: ~20-25 minutes)

## 📋 What Gets Generated

The script creates hero images with these themes:

1. **Dark Abstract Coral Ribbons**: Flowing gradients on dark background
2. **Floating Geometric Shapes**: 3D shapes with coral/salmon gradients
3. **Abstract Waves**: Liquid motion graphics
4. **Particle Field**: Glowing particles in dark space
5. **Geometric Gradient**: Low poly abstract with gradient overlay

All images:
- **Resolution**: 1920x1080 (perfect for hero sections)
- **Colors**: Coral (#FF6E6B) and Salmon (#FF8E53) accents on dark charcoal (#0a0a0a)
- **Style**: Modern, minimalist, professional tech aesthetic

## 🎨 Using Generated Assets

### 1. Review Generated Images

```bash
# List generated files
ls -lh assets/generated/heroes/

# Open folder to preview
open assets/generated/heroes/  # macOS
xdg-open assets/generated/heroes/  # Linux
```

### 2. Serve Assets via FastAPI

Add static file serving to your FastAPI app:

```python
# In apps/creator/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
```

### 3. Update Templates

Replace CSS gradients with AI-generated backgrounds:

**Before** ([auth.html](apps/web/templates/auth.html)):
```css
body {
    background: var(--bg-dark);
}
```

**After**:
```css
body {
    background: var(--bg-dark) url('/assets/generated/heroes/prompt_abc_0.png') no-repeat center center;
    background-size: cover;
}
```

### 4. A/B Test Different Versions

Generate multiple variations and test:

```python
# Serve different backgrounds based on user segment
if user.segment == "A":
    background = "/assets/generated/heroes/version_1.png"
else:
    background = "/assets/generated/heroes/version_2.png"
```

## 🛠 Customization

### Modify Prompts

Edit `HERO_PROMPTS` in [scripts/generate_hero_images.py](scripts/generate_hero_images.py):

```python
HERO_PROMPTS = [
    "your custom prompt here, dark theme, coral accents, modern tech aesthetic",
    # Add more prompts...
]
```

### Change Resolution

Update the workflow dimensions:

```python
"5": {
    "inputs": {
        "width": 2560,   # Change to desired width
        "height": 1440,  # Change to desired height
        "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
}
```

### Use Your Own Workflow

1. Open ComfyUI web interface
2. Design your custom workflow
3. Click "Save (API Format)" to export JSON
4. Replace `HERO_IMAGE_WORKFLOW` in the script

## 📊 Asset Management Strategy

### Versioning

Keep track of which assets are deployed:

```bash
# Create symlinks for active assets
cd assets/generated/heroes/
ln -sf prompt_abc123_0.png active_login_bg.png
ln -sf prompt_def456_0.png active_dashboard_bg.png

# Reference in templates
background-image: url('/assets/generated/heroes/active_login_bg.png');
```

### Archive Old Versions

```bash
mkdir -p assets/generated/heroes/archive/2025-01/
mv assets/generated/heroes/old_*.png assets/generated/heroes/archive/2025-01/
```

### Optimization for Production

```bash
# Install optimization tools
pip install pillow

# Optimize PNGs (lossy compression)
python -c "
from PIL import Image
import glob

for img_path in glob.glob('assets/generated/heroes/*.png'):
    img = Image.open(img_path)
    img.save(img_path, optimize=True, quality=85)
    print(f'Optimized: {img_path}')
"

# Or convert to WebP for better compression
python -c "
from PIL import Image
import glob

for img_path in glob.glob('assets/generated/heroes/*.png'):
    img = Image.open(img_path)
    webp_path = img_path.replace('.png', '.webp')
    img.save(webp_path, 'webp', quality=90)
    print(f'Converted: {webp_path}')
"
```

## 🎯 Next Steps

1. **Start ComfyUI**: Get your ComfyUI server running (local or RunPod)
2. **Run Script**: `python scripts/generate_hero_images.py`
3. **Review Images**: Check `assets/generated/heroes/`
4. **Pick Favorites**: Choose the best ones for your brand
5. **Update Templates**: Replace CSS gradients with generated backgrounds
6. **Deploy**: Push to production

## 💡 Future Ideas

### Expand Asset Types

Generate more than just hero images:

- **Icons**: Generate consistent icon sets
- **Empty States**: Custom "no results" illustrations
- **Loading Animations**: Animated backgrounds or spinners
- **Social Media**: Auto-generate OG images for blog posts
- **Email Headers**: Custom email templates
- **Feature Illustrations**: Showcase pages

### Dynamic Generation

Build an admin panel to generate assets on-demand:

```python
@router.post("/admin/generate-asset")
async def generate_asset(
    prompt: str,
    asset_type: str,
    current_user: User = Depends(require_admin),
):
    """Generate design asset via admin panel"""
    # Use ComfyUI client to generate
    # Save to assets/generated/
    # Return preview URL
```

### User-Specific Assets

Generate personalized backgrounds for each user:

```python
# Generate unique background for user
prompt = f"abstract tech background, {user.favorite_color} theme, professional"
bg_image = await generate_user_background(user.id, prompt)
```

## 📈 Success Metrics

Track how AI-generated assets perform:

- **Engagement**: Time on page with AI backgrounds vs. gradients
- **Conversion**: Signup rate with different hero images
- **User Feedback**: Surveys on design preferences
- **Brand Perception**: Does it feel more unique/premium?

## 🎨 Brand Guidelines

When creating prompts, always include:

1. **Color Palette**: Coral (#FF6E6B), Salmon (#FF8E53), Dark Charcoal (#0a0a0a)
2. **Style Keywords**: modern, minimalist, professional, tech aesthetic
3. **Quality Keywords**: 4k, ultra sharp, premium quality, cinematic
4. **Avoid**: text, watermarks, logos, recognizable objects

## 📚 Resources

- **ComfyUI Docs**: https://github.com/comfyanonymous/ComfyUI
- **Your Integration**: [apps/shared/services/comfyui/](apps/shared/services/comfyui/)
- **Asset README**: [assets/generated/README.md](assets/generated/README.md)
- **RunPod Setup**: See [docs/runpod/](docs/runpod/) (if you have RunPod docs)

---

**Built with Creator** 🚀
Demonstrating the platform by using it to build itself.
