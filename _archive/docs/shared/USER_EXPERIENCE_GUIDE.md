# User Experience Guide - How People Use Your API

## 🎯 Overview

This guide shows **exactly** how different users would interact with your ComfyUI API Service, including all parameters they can control.

---

## 📱 User Journey: From Signup to First Image

### Step 1: Sign Up (30 seconds)

**What the user sees:**

```
Landing page → "Start Free Trial" button
  ↓
Email signup form
  ↓
Email confirmation
  ↓
Dashboard with API key
```

**What they get:**
```json
{
  "api_key": "sk_live_abc123xyz789",
  "tier": "free",
  "quota": {
    "images_included": 50,
    "images_used": 0,
    "images_remaining": 50,
    "resets_at": "2025-12-01T00:00:00Z"
  }
}
```

---

### Step 2: Make First API Call (2 minutes)

**Simplest possible example:**

```bash
curl -X POST https://api.yourservice.com/v1/generate \
  -H "Authorization: Bearer sk_live_abc123xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful sunset"
  }'
```

**Response (1-2 seconds later):**
```json
{
  "job_id": "img_abc123",
  "status": "completed",
  "image_url": "https://cdn.yourservice.com/images/img_abc123.png",
  "generation_time": 1.2,
  "cost": {
    "images_used": 1,
    "quota_remaining": 49
  }
}
```

**User downloads the image and sees their sunset!** 🌅

---

## 🎛️ All Available Parameters

### Basic Text-to-Image Parameters

```python
import requests

response = requests.post(
    "https://api.yourservice.com/v1/generate",
    headers={"Authorization": "Bearer sk_live_abc123xyz789"},
    json={
        # REQUIRED
        "prompt": "a majestic mountain landscape",

        # OPTIONAL - Image dimensions
        "width": 512,           # Default: 512, Range: 64-2048, Must be divisible by 8
        "height": 512,          # Default: 512, Range: 64-2048, Must be divisible by 8

        # OPTIONAL - Generation quality
        "steps": 20,            # Default: 20, Range: 1-150 (higher = better quality, slower)
        "cfg_scale": 7.0,       # Default: 7.0, Range: 1-30 (how closely to follow prompt)
        "sampler_name": "euler_ancestral",  # Options: euler, euler_ancestral, dpm_2, etc.

        # OPTIONAL - Randomness control
        "seed": 42,             # Default: random, Range: 0-4294967295 (for reproducibility)

        # OPTIONAL - Negative prompt (what to avoid)
        "negative_prompt": "blurry, low quality, distorted",

        # OPTIONAL - Batch generation
        "num_images": 1,        # Default: 1, Range: 1-4 (how many variations to generate)

        # OPTIONAL - Model selection
        "model": "sd_xl_base_1.0.safetensors"  # Default model if not specified
    }
)

result = response.json()
print(f"Image URL: {result['image_url']}")
```

---

## 👤 User Persona Examples

### Example 1: Mobile App Developer (Sarah)

**What Sarah is building:** "AI Headshot Pro" - iOS app

**Her use case:**
1. User uploads a selfie
2. App generates professional headshot
3. User downloads result

**Her API call:**

```python
# In her iOS backend (Python/Flask)
import requests
import base64

def generate_headshot(selfie_image):
    # Convert user's selfie to base64
    selfie_base64 = base64.b64encode(selfie_image).decode()

    response = requests.post(
        "https://api.yourservice.com/v1/generate",
        headers={"Authorization": f"Bearer {SARAH_API_KEY}"},
        json={
            "prompt": "professional business headshot, corporate attire, studio lighting, high quality",
            "negative_prompt": "casual clothes, outdoor, low quality, blurry",
            "width": 512,
            "height": 768,  # Portrait orientation
            "steps": 25,     # Higher quality
            "cfg_scale": 7.5,
            "seed": None,    # Random each time
            "num_images": 3  # Generate 3 variations
        }
    )

    return response.json()

# Result Sarah gets:
# {
#   "job_id": "img_xyz789",
#   "status": "completed",
#   "images": [
#     {"url": "https://.../headshot_1.png", "seed": 12345},
#     {"url": "https://.../headshot_2.png", "seed": 67890},
#     {"url": "https://.../headshot_3.png", "seed": 24680}
#   ],
#   "generation_time": 2.3,
#   "cost": {
#     "images_used": 3,
#     "quota_remaining": 2997
#   }
# }
```

**What her users see:**
1. Upload selfie
2. Wait 2-3 seconds
3. Choose from 3 professional headshots
4. Download favorite

**Sarah's monthly usage:**
- 1,000 users/month × 3 headshots = 3,000 images
- **Cost: $99/month (Pro tier)**

---

### Example 2: Marketing Agency (Digital Boost)

**What they're building:** Facebook ad campaigns with product photography

**Their use case:**
1. Client sends product photo
2. Generate 50 background variations
3. A/B test to find best performer

**Their API call:**

```javascript
// In their web dashboard (Node.js)
const axios = require('axios');

async function generateProductBackgrounds(productImageUrl) {
    // Generate multiple variations with different backgrounds
    const backgrounds = [
        "product on white marble surface",
        "product on wooden table, natural lighting",
        "product on beach sand, sunset background",
        "product in modern kitchen, bright lighting",
        "product in luxury setting, gold accents"
    ];

    const results = [];

    for (const background of backgrounds) {
        const response = await axios.post(
            'https://api.yourservice.com/v1/generate',
            {
                prompt: `${background}, professional product photography, high quality, 8k`,
                negative_prompt: "blurry, low quality, distorted, bad lighting",
                width: 1024,        // Instagram square
                height: 1024,
                steps: 30,          // High quality for ads
                cfg_scale: 8.0,     // Follow prompt closely
                num_images: 10      // 10 variations per background
            },
            {
                headers: {
                    'Authorization': `Bearer ${process.env.API_KEY}`
                }
            }
        );

        results.push(response.data);
    }

    return results;
}

// They get: 5 backgrounds × 10 variations = 50 images
// Total time: ~30 seconds
// Cost: 50 images from their monthly quota
```

**What the agency does:**
1. Upload client's product photo
2. Click "Generate Ad Variations"
3. Get 50 different backgrounds in 30 seconds
4. Export to Facebook Ads Manager
5. A/B test to find winner

**Their monthly usage:**
- 10 clients × 5 products × 50 variations = 2,500 images
- **Cost: $99/month (Pro tier)**

---

### Example 3: SaaS Company (DesignHub - Canva Competitor)

**What they're building:** Design tool with AI features

**Their use case:**
1. 10,000 users
2. Each generates ~5 AI images/month
3. Need it embedded in their app

**Their integration:**

```typescript
// In their React app
import axios from 'axios';

class DesignHubAI {
    private apiKey: string;
    private baseUrl = 'https://api.yourservice.com/v1';

    constructor(apiKey: string) {
        this.apiKey = apiKey;
    }

    async generateImage(params: {
        prompt: string;
        width?: number;
        height?: number;
        style?: 'realistic' | 'artistic' | 'cartoon';
    }) {
        // Map user-friendly options to technical parameters
        const stylePresets = {
            realistic: {
                steps: 25,
                cfg_scale: 7.0,
                sampler: 'euler_ancestral'
            },
            artistic: {
                steps: 30,
                cfg_scale: 9.0,
                sampler: 'dpm_2'
            },
            cartoon: {
                steps: 20,
                cfg_scale: 8.0,
                sampler: 'euler'
            }
        };

        const preset = stylePresets[params.style || 'realistic'];

        const response = await axios.post(
            `${this.baseUrl}/generate`,
            {
                prompt: params.prompt,
                width: params.width || 512,
                height: params.height || 512,
                steps: preset.steps,
                cfg_scale: preset.cfg_scale,
                sampler_name: preset.sampler
            },
            {
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`
                }
            }
        );

        return response.data;
    }

    // Check user's quota before generation
    async checkQuota(userId: string) {
        const response = await axios.get(
            `${this.baseUrl}/users/${userId}/quota`,
            {
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`
                }
            }
        );

        return response.data;
    }
}

// In their UI component
function AIImageGenerator() {
    const [prompt, setPrompt] = useState('');
    const [style, setStyle] = useState('realistic');
    const [quota, setQuota] = useState(null);

    const handleGenerate = async () => {
        // Show loading state
        setLoading(true);

        try {
            const result = await designHubAI.generateImage({
                prompt,
                width: 1024,
                height: 1024,
                style
            });

            // Show image to user
            displayImage(result.image_url);

            // Update quota display
            setQuota(result.cost.quota_remaining);
        } catch (error) {
            if (error.response?.status === 429) {
                // User hit rate limit
                showUpgradeModal();
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe your image..."
            />
            <select value={style} onChange={(e) => setStyle(e.target.value)}>
                <option value="realistic">Realistic</option>
                <option value="artistic">Artistic</option>
                <option value="cartoon">Cartoon</option>
            </select>
            <button onClick={handleGenerate}>Generate</button>
            {quota && <p>Credits remaining: {quota}</p>}
        </div>
    );
}
```

**What their end users see:**
1. Type description: "a cat wearing a hat"
2. Choose style: Realistic / Artistic / Cartoon
3. Click "Generate AI Image"
4. Wait 2 seconds
5. Image appears in their design

**DesignHub's monthly usage:**
- 10,000 users × 5 images = 50,000 images/month
- **Cost: $2,500/month (Enterprise with volume discount)**

---

## 🎨 Advanced Features Users Can Control

### 1. Image-to-Image (Style Transfer)

**Use case:** "Make my photo look like a painting"

```python
response = requests.post(
    "https://api.yourservice.com/v1/generate",
    headers={"Authorization": "Bearer sk_live_abc123"},
    json={
        "prompt": "oil painting, impressionist style",
        "init_image": "https://example.com/my-photo.jpg",  # Source image
        "strength": 0.7,  # How much to change (0.0-1.0)
        "width": 512,
        "height": 512,
        "steps": 25
    }
)
```

**What the user gets:**
- Their photo transformed into an oil painting
- `strength=0.3` = subtle changes (still recognizable)
- `strength=0.9` = dramatic changes (barely recognizable)

---

### 2. Inpainting (Edit Part of Image)

**Use case:** "Remove this object from my photo"

```python
response = requests.post(
    "https://api.yourservice.com/v1/generate",
    headers={"Authorization": "Bearer sk_live_abc123"},
    json={
        "prompt": "empty street, no people",
        "init_image": "https://example.com/street-photo.jpg",
        "mask_image": "https://example.com/mask.png",  # White = edit, Black = keep
        "width": 512,
        "height": 512,
        "steps": 30
    }
)
```

**What the user gets:**
- Original image with masked area regenerated
- Perfect for removing objects, changing backgrounds, etc.

---

### 3. ControlNet (Precise Control)

**Use case:** "Generate image matching this pose"

```python
response = requests.post(
    "https://api.yourservice.com/v1/generate",
    headers={"Authorization": "Bearer sk_live_abc123"},
    json={
        "prompt": "superhero in dynamic pose",
        "controlnet_type": "openpose",  # Options: openpose, canny, depth, etc.
        "control_image": "https://example.com/pose.jpg",  # Reference pose
        "controlnet_strength": 0.8,  # How strictly to follow control (0.0-1.0)
        "width": 512,
        "height": 768,
        "steps": 25
    }
)
```

**What the user gets:**
- New image that matches the pose/structure of control image
- Different styles: openpose (poses), canny (edges), depth (3D structure)

---

### 4. Upscaling (Make Image Bigger)

**Use case:** "Make this image 4x larger"

```python
response = requests.post(
    "https://api.yourservice.com/v1/upscale",
    headers={"Authorization": "Bearer sk_live_abc123"},
    json={
        "image": "https://example.com/small-image.jpg",
        "scale": 4,  # Options: 2, 4 (2x or 4x bigger)
        "model": "realesrgan"  # Upscaling model
    }
)
```

**What the user gets:**
- 512×512 image → 2048×2048 image
- Enhanced details, sharper quality

---

### 5. Batch Processing (Multiple Images)

**Use case:** "Generate 100 product variations overnight"

```python
# Submit batch job (asynchronous)
response = requests.post(
    "https://api.yourservice.com/v1/batch",
    headers={"Authorization": "Bearer sk_live_abc123"},
    json={
        "jobs": [
            {
                "prompt": "product on white background, variation 1",
                "width": 1024,
                "height": 1024,
                "seed": i
            }
            for i in range(100)  # 100 variations
        ],
        "webhook_url": "https://myapp.com/webhook"  # Get notified when done
    }
)

batch_id = response.json()["batch_id"]

# Check status later
status = requests.get(
    f"https://api.yourservice.com/v1/batch/{batch_id}",
    headers={"Authorization": "Bearer sk_live_abc123"}
)

# {
#   "batch_id": "batch_xyz",
#   "status": "processing",
#   "completed": 45,
#   "total": 100,
#   "results": [...]  # URLs to completed images
# }
```

**What the user gets:**
- Submit 100 jobs at once
- Get webhook notification when complete
- Download all results as ZIP

---

## 📊 User Dashboard Features

### What Users See After Login

```
┌─────────────────────────────────────────────────────┐
│ Dashboard                                            │
├─────────────────────────────────────────────────────┤
│                                                      │
│ 📊 Usage This Month                                 │
│ ├─ Images Generated: 1,247 / 5,000                 │
│ ├─ Quota Remaining: 3,753                          │
│ ├─ Resets: Dec 1, 2025                             │
│ └─ [Upgrade to Pro →]                               │
│                                                      │
│ 🔑 API Keys                                         │
│ ├─ Production: sk_live_abc123... [Show] [Rotate]   │
│ └─ [+ Create New Key]                               │
│                                                      │
│ 📈 Recent Activity                                  │
│ ├─ Nov 8, 10:23 AM - Generated 3 images           │
│ ├─ Nov 8, 10:15 AM - Generated 1 image            │
│ └─ Nov 7, 2:45 PM - Generated 5 images            │
│                                                      │
│ 💳 Billing                                          │
│ ├─ Current Plan: Pro ($99/month)                   │
│ ├─ Next Billing: Dec 1, 2025                       │
│ ├─ Payment Method: •••• 4242                       │
│ └─ [View Invoices] [Update Payment]                │
│                                                      │
│ 📚 Resources                                        │
│ ├─ [API Documentation]                              │
│ ├─ [Code Examples]                                  │
│ ├─ [Community Discord]                              │
│ └─ [Support]                                        │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Developer Tools Available

### 1. Interactive Playground

**What it is:** Web-based testing tool

**How it works:**
```
User visits: https://api.yourservice.com/playground

┌────────────────────────────────────────┐
│ API Playground                          │
├────────────────────────────────────────┤
│                                         │
│ Prompt: [a beautiful sunset________]   │
│                                         │
│ Advanced Options ▼                      │
│ ├─ Width: [512]  Height: [512]        │
│ ├─ Steps: [20]   CFG Scale: [7.0]     │
│ └─ Seed: [Random ▼]                    │
│                                         │
│ [Generate Image]                        │
│                                         │
│ Result:                                 │
│ ┌─────────────────┐                    │
│ │                 │                    │
│ │  [Image here]   │                    │
│ │                 │                    │
│ └─────────────────┘                    │
│                                         │
│ Code to reproduce:                      │
│ ```python                               │
│ response = requests.post(...)          │
│ ```                                     │
│                                         │
└────────────────────────────────────────┘
```

**Value for users:**
- Test API without writing code
- See exact code to copy
- Experiment with parameters

---

### 2. SDKs (Software Development Kits)

**Python SDK:**

```python
# Install
pip install comfyui-api

# Use
from comfyui_api import Client

client = Client(api_key="sk_live_abc123")

# Simple generation
image = client.generate("a beautiful sunset")
print(f"Image URL: {image.url}")

# Advanced generation
image = client.generate(
    prompt="professional headshot",
    width=512,
    height=768,
    steps=25,
    cfg_scale=7.5,
    negative_prompt="blurry, low quality"
)

# Async generation
job = client.generate_async("landscape painting")
job.wait()  # Block until complete
print(job.result.url)

# Or use webhooks
job = client.generate_async(
    "landscape painting",
    webhook_url="https://myapp.com/webhook"
)
```

**JavaScript SDK:**

```javascript
// Install
npm install @comfyui/api-client

// Use
import { ComfyUIClient } from '@comfyui/api-client';

const client = new ComfyUIClient({
  apiKey: 'sk_live_abc123'
});

// Simple generation
const image = await client.generate({
  prompt: 'a beautiful sunset'
});
console.log('Image URL:', image.url);

// With options
const image = await client.generate({
  prompt: 'professional headshot',
  width: 512,
  height: 768,
  steps: 25,
  negativePrompt: 'blurry, low quality'
});

// Async with webhook
const job = await client.generateAsync({
  prompt: 'landscape painting',
  webhookUrl: 'https://myapp.com/webhook'
});
```

---

### 3. CLI Tool

**Command line interface:**

```bash
# Install
npm install -g @comfyui/cli

# Configure
comfyui config set-key sk_live_abc123

# Generate
comfyui generate "a beautiful sunset"
# → Saves to: sunset_abc123.png

# With options
comfyui generate "professional headshot" \
  --width 512 \
  --height 768 \
  --steps 25 \
  --output headshot.png

# Batch generation
comfyui batch prompts.txt --output-dir ./results/
```

---

## 💰 Billing & Usage Tracking

### How Users Monitor Their Usage

**1. Real-time Dashboard:**

```
Current Month Usage
─────────────────────────────────────────
Images Generated:     1,247 / 5,000
Quota Remaining:      3,753 images
Estimated Overage:    $0.00
Next Reset:           Dec 1, 2025

Daily Breakdown:
Nov 8: ████████░░ 234 images
Nov 7: ███░░░░░░░  87 images
Nov 6: ██████████ 456 images
```

**2. Usage API:**

```python
# Check quota programmatically
response = requests.get(
    "https://api.yourservice.com/v1/usage",
    headers={"Authorization": "Bearer sk_live_abc123"}
)

# {
#   "quota": {
#     "included": 5000,
#     "used": 1247,
#     "remaining": 3753,
#     "overage": 0,
#     "resets_at": "2025-12-01T00:00:00Z"
#   },
#   "current_period": {
#     "start": "2025-11-01T00:00:00Z",
#     "end": "2025-12-01T00:00:00Z"
#   }
# }
```

**3. Email Alerts:**

Users get automatic emails:
- 80% quota used: "You've used 4,000/5,000 images"
- 100% quota: "You've reached your limit. Upgrade or wait for reset."
- Overage charges: "You used 100 extra images = $2.50"

---

## 🎯 Complete User Flow Examples

### Flow 1: First-Time User (Sarah - iOS Developer)

**Timeline: Day 1**

```
10:00 AM - Finds your service via Google search
         "ai image generation api"

10:05 AM - Lands on homepage
         Reads: "ComfyUI API for Developers"
         Clicks: "Start Free Trial"

10:06 AM - Creates account
         Email: sarah@example.com
         Password: ••••••••

10:07 AM - Email verification
         Clicks link in email

10:08 AM - Dashboard appears
         API Key shown: sk_live_abc123xyz789
         Free quota: 50 images

10:10 AM - Tries playground
         Prompt: "professional headshot"
         Clicks Generate
         Image appears in 2 seconds ✨

10:15 AM - Copies code example
         Pastes into her app
         Makes first API call
         Success! 🎉

10:30 AM - Shows boss
         Boss approves budget

10:35 AM - Upgrades to Pro ($99/month)
         Gets 5,000 images/month
         Starts building feature
```

**What convinced Sarah:**
1. Worked immediately (free tier)
2. Simple API (one curl command)
3. Fast (2 second generation)
4. Affordable ($99 for 5,000 images)

---

### Flow 2: Agency Team (Digital Boost)

**Timeline: Week 1**

```
Monday:
├─ Marketing Manager discovers service
├─ Tests with free account
├─ Generates 20 product backgrounds
└─ Shows team → Everyone impressed

Tuesday:
├─ Developer integrates API
├─ Builds internal tool
└─ 2 hours of work total

Wednesday:
├─ Designer tests with real client work
├─ Generates 50 variations
└─ Client approves 5 concepts

Thursday:
├─ Team decides to subscribe
├─ Upgrades to Business ($299/month)
└─ Gets 20,000 images/month

Friday:
├─ Uses for 3 client campaigns
├─ Generates 500 images total
└─ Saves ~$2,000 in designer time
```

**ROI for agency:**
- Cost: $299/month
- Saves: 10 hours × $200/hour = $2,000/month
- **Net benefit: $1,700/month**

---

### Flow 3: SaaS Company (DesignHub)

**Timeline: Month 1-3**

```
Month 1:
├─ CTO evaluates options
├─ Tests your API vs competitors
├─ Your API wins (full ComfyUI features)
├─ Engineers integrate in 1 week
└─ Beta test with 100 users

Month 2:
├─ Beta successful
├─ Roll out to 1,000 users
├─ Generate ~5,000 images
└─ Subscribe to Business tier ($299/month)

Month 3:
├─ Feature popular
├─ 10,000 users now using it
├─ Generating ~50,000 images/month
├─ Negotiate enterprise contract
└─ Custom pricing: $2,500/month (volume discount)
```

**Value for DesignHub:**
- Feature differentiates from competitors
- Increases user engagement by 40%
- Drives upgrades to premium tier
- **Additional revenue: $50,000/month**

**They're happy to pay $2,500/month for $50k revenue!**

---

## 🎨 Parameter Guide Summary

### Essential Parameters (Every User Needs)

| Parameter | What It Does | Example |
|-----------|--------------|---------|
| `prompt` | Describes desired image | "a sunset over mountains" |
| `width` | Image width in pixels | 512, 1024, 2048 |
| `height` | Image height in pixels | 512, 1024, 2048 |
| `steps` | Quality vs speed tradeoff | 10=fast, 30=high quality |
| `seed` | Reproducibility | 42 (same seed = same image) |

### Advanced Parameters (Power Users)

| Parameter | What It Does | When to Use |
|-----------|--------------|-------------|
| `negative_prompt` | What to avoid | "no people, no text, no blur" |
| `cfg_scale` | Prompt strictness | Higher = closer to prompt |
| `sampler_name` | Algorithm choice | Different styles/qualities |
| `num_images` | Batch generation | Generate variations at once |
| `init_image` | Source image | Image-to-image transformations |
| `strength` | Change intensity | 0.3=subtle, 0.9=dramatic |
| `controlnet_type` | Control method | Pose, edges, depth, etc. |

### Pro Parameters (Enterprises)

| Parameter | What It Does | Who Uses It |
|-----------|--------------|-------------|
| `webhook_url` | Async notifications | Large batch jobs |
| `priority` | Queue priority | Paid for faster processing |
| `custom_model` | Use trained model | Companies with branded style |
| `watermark` | Add branding | White-label users |

---

## 💡 Key Takeaways

**Users interact through:**
1. **Simple API calls** - Just prompt + API key for basics
2. **Advanced parameters** - Full control when needed
3. **SDKs/libraries** - Language-specific convenience
4. **Web dashboard** - Monitor usage, manage billing
5. **Playground** - Test without coding

**They can control:**
- Image size, quality, style
- Processing speed vs quality tradeoff
- Reproducibility (seeds)
- Batch sizes
- Advanced features (ControlNet, inpainting, etc.)

**The experience is:**
- ✅ Simple for beginners (just prompt)
- ✅ Powerful for experts (100+ parameters)
- ✅ Fast (1-2 second responses)
- ✅ Transparent (see usage in real-time)
- ✅ Predictable (clear pricing, no surprises)

---

*This is how real users would interact with your service every day.* 🚀
