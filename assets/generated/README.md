# AI-Generated Design Assets

This directory contains design assets generated using the Creator platform's own ComfyUI integration.

## Philosophy

We use our own product to create the product's design assets. This approach:
- Validates that our platform works
- Creates unique, custom assets
- Allows rapid iteration and A/B testing
- Demonstrates the product's capabilities

## Directory Structure

```
assets/generated/
├── heroes/          # Hero/background images for landing pages
├── backgrounds/     # Generic background patterns
├── icons/           # Custom icon variations
├── illustrations/   # Feature illustrations
└── marketing/       # Marketing and social media assets
```

## Generation Workflow

### 1. Generate Assets

```bash
# Generate hero images
python scripts/generate_hero_images.py

# Or customize generation
python scripts/generate_hero_images.py --count 10 --theme dark-purple
```

### 2. Review and Curate

Browse generated images in `assets/generated/heroes/` and select your favorites.

### 3. Deploy to Templates

Update HTML templates to use the generated assets:

```html
<!-- auth.html -->
<body style="background-image: url('/assets/generated/heroes/[prompt_id]_0.png');">
```

### 4. Version Control

Keep track of which assets are currently in use:

```bash
# Create symlinks to "active" assets
ln -s heroes/prompt_abc_0.png heroes/active_login_bg.png
ln -s heroes/prompt_xyz_0.png heroes/active_dashboard_bg.png
```

## Brand Prompts

Our core prompts emphasize:
- **Colors**: Dark charcoal background (#0a0a0a) with coral (#FF6E6B) and salmon (#FF8E53) accents
- **Style**: Modern, minimalist, geometric, professional tech aesthetic
- **Mood**: Premium, cinematic, high contrast

Example prompts:
- "abstract digital art, dark charcoal background, flowing coral and salmon gradient ribbons..."
- "3d geometric shapes floating in dark space, coral red and salmon orange gradients..."

## A/B Testing

Generate multiple variations and test which performs better:

1. Generate 5 variations of login background
2. Deploy different versions to different users
3. Track engagement metrics
4. Keep the winner

## Technical Details

### ComfyUI Workflow

The generation uses a Stable Diffusion 1.5 text-to-image workflow:
- Model: SD 1.5 (v1-5-pruned-emaonly.ckpt)
- Resolution: 1920x1080 (16:9 for hero sections)
- Steps: 25
- Sampler: DPM++ 2M Karras (best for smooth gradients)
- CFG: 7.5
- Scheduler: Karras

Note: You can use any SD-compatible model. SDXL would provide higher quality but requires more VRAM and longer generation times.

### Customization

To customize the workflow:
1. Open ComfyUI web interface
2. Design your workflow
3. Export workflow JSON (Save API Format)
4. Update `HERO_IMAGE_WORKFLOW` in `scripts/generate_hero_images.py`

## Asset Management

### Storage

- **Development**: Local `assets/generated/` directory
- **Production**: Should be served from CDN (Cloudflare, AWS CloudFront, etc.)

### Optimization

Before deploying to production:
```bash
# Optimize PNGs
pngquant assets/generated/heroes/*.png --ext .png --force

# Or convert to WebP
cwebp -q 90 assets/generated/heroes/input.png -o assets/generated/heroes/output.webp
```

### Serving

Serve assets via FastAPI static files:

```python
# In main.py
from fastapi.staticfiles import StaticFiles

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
```

## Examples

Current hero images generated with Creator:

| Prompt ID | Theme | Used In | Status |
|-----------|-------|---------|--------|
| `abc123` | Dark Coral Waves | Login page | Active |
| `def456` | Floating Particles | Dashboard | Testing |
| `ghi789` | Geometric Gradient | Landing page | Archived |

## Future Ideas

- **Seasonal themes**: Generate holiday-themed backgrounds
- **Dynamic generation**: Generate personalized backgrounds per user
- **Interactive backgrounds**: Generate video loops instead of static images
- **Icon sets**: Generate consistent icon families
- **Illustration library**: Build a library of custom illustrations

## Notes

- Keep archives of all generated assets (you might want to revert)
- Document which prompts created which assets
- Track performance metrics for A/B testing
- Consider user preferences (dark mode, light mode)

---

**Generated with Creator** 🎨
Using our own platform to build our own platform.
