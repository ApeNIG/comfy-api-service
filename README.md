# ComfyUI Platform

**AI-Powered Image Generation & Automation**

Two products, one powerful backend:
- **API Product** - Developer API for AI image generation
- **Creator Product** - Automated editing for indie creators (Coming Soon)

---

## 🚀 Quick Start

### For API Users (Developers)

```bash
# 1. Start RunPod GPU instance
python manage_runpod.py start

# 2. Start local services
docker compose up -d

# 3. Generate an image
curl -X POST http://localhost:8000/api/v1/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "width": 512,
    "height": 512
  }'
```

**[→ Read Full API Documentation](_archive/docs/api/)**

### For Creators (End Users)

🚧 **Coming Soon** - Automated photo editing via Google Drive

Upload photos → System auto-edits → Download results

**[→ Read Creator Product Plan](_archive/docs/creator/)**

---

## 📚 Documentation

### 📖 Product Documentation

- **[API Product](_archive/docs/api/)** - Developer API documentation
  - [RunPod Integration Guide](_archive/docs/api/README_RUNPOD.md)
  - [API Testing Guide](_archive/docs/api/API_TESTING_GUIDE.md)
  - [Robustness Assessment](_archive/docs/api/ROBUSTNESS_ASSESSMENT.md)

- **[Creator Product](_archive/docs/creator/)** - End-user automation (MVP in progress)
  - [Quick Start Guide](_archive/docs/creator/QUICK_START.md)
  - [Project Plan](_archive/docs/creator/MVP_PROJECT_PLAN.md)
  - [Feature Specifications](_archive/docs/creator/CREATOR_FEATURES.md)
  - [Database Schema](_archive/docs/creator/DATABASE_SCHEMA.md)

- **[Shared Documentation](_archive/docs/shared/)** - Applies to both products
  - [Business Model](_archive/docs/shared/BUSINESS_MODEL.md)
  - [User Experience Guide](_archive/docs/shared/USER_EXPERIENCE_GUIDE.md)
  - [API Integration Strategy](_archive/docs/shared/API_INTEGRATION.md)

### 🛠️ General Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture overview
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[QUICKSTART.md](QUICKSTART.md)** - General quickstart guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Implementation details

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│          FastAPI Application (Port 8000)            │
│                                                     │
│  ┌────────────────┐        ┌────────────────────┐  │
│  │   API Routes   │        │  Creator Routes    │  │
│  │  /api/v1/*     │        │  /creator/*        │  │
│  │                │        │                    │  │
│  │ Auth: API Key  │        │ Auth: OAuth        │  │
│  └───────┬────────┘        └─────────┬──────────┘  │
│          │                           │             │
└──────────┼───────────────────────────┼─────────────┘
           │                           │
           ▼                           ▼
    ┌──────────────────────────────────────────┐
    │        Shared Services Layer             │
    │  - ComfyUI Client (RunPod)               │
    │  - Storage (MinIO / Google Drive)        │
    │  - Job Queue (Dramatiq + Redis)          │
    └──────────────────────────────────────────┘
```

**Two products, one backend** - Clean separation via routing, shared infrastructure for efficiency.

---

## 🎯 Product Comparison

| Feature | API Product | Creator Product |
|---------|-------------|-----------------|
| **Status** | ✅ Production Ready | 🚧 MVP in Progress |
| **Target Users** | Developers | Indie Creators |
| **Use Case** | Integrate AI into apps | Auto-edit photos |
| **Authentication** | API Key | OAuth (Google) |
| **Pricing** | Usage-based | Subscription ($29/mo) |
| **Storage** | MinIO (S3) | Google Drive |
| **Launch Date** | 2025-11 | 2026-01 (Week 8) |

---

## 📊 Status

### API Product
- ✅ **Production Ready**
- ✅ 100% robustness test pass rate (14/14 tests)
- ✅ RunPod GPU integration working
- ✅ Sub-2-second generation times
- ✅ Sync and async endpoints tested

### Creator Product
- 🚧 **MVP in Development** (Phase 1: Foundation)
- 📅 Target Launch: Week 8 (8 weeks from 2025-11-10)
- 📝 Full documentation complete
- 🎯 Next: Directory structure + storage abstraction

---

## 🚀 Getting Started

### Prerequisites

```bash
# Required
- Python 3.11+
- Docker & Docker Compose
- RunPod account (for GPU)

# Optional
- Google Cloud account (for Creator product)
- Stripe account (for Creator billing)
```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/comfy-api-service.git
cd comfy-api-service

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services
docker compose up -d

# Start RunPod (for API product)
python manage_runpod.py start
```

---

## 🛠️ Development

### Project Structure

```
comfy-api-service/
├── apps/
│   ├── api/         # API product (FastAPI)
│   ├── creator/     # Creator product (in progress)
│   ├── worker/      # Background job processor
│   └── web/         # Creator dashboard UI
├── _archive/docs/
│   ├── api/         # API documentation
│   ├── creator/     # Creator documentation
│   └── shared/      # Shared documentation
├── sdk/             # Python SDK
├── workflows/       # ComfyUI workflows
└── docker-compose.yml
```

### Running Tests

```bash
# API tests
cat test_robustness.py | docker run --rm -i \
  --network comfy-api-service_comfyui-network \
  python:3.11-slim bash -c "pip install -q requests && python -"

# Expected: 14/14 tests passed (100%)
```

---

## 💰 Business Model

### API Product (Developer Tier)
- **Model:** Usage-based pricing (per image/API call)
- **Target:** SaaS companies, agencies, developers
- **Pricing:** $0.01-0.05 per image (volume discounts)

### Creator Product (End-User Tier)
- **Free:** 10 images/month
- **Creator ($29/mo):** 100 images/month, no watermark
- **Studio ($99/mo):** 500 images/month, custom presets

**[→ Read Full Business Model](_archive/docs/shared/BUSINESS_MODEL.md)**

---

## 🤝 Contributing

We welcome contributions! Please read our contributing guidelines (coming soon).

---

## 📄 License

*To be determined*

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/comfy-api-service/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/comfy-api-service/discussions)
- **Email:** support@yourservice.com (coming soon)

---

## 🙏 Acknowledgments

- ComfyUI - Powerful Stable Diffusion UI
- RunPod - GPU infrastructure
- FastAPI - Modern Python web framework
- Dramatiq - Distributed task processing

---

**Built with ❤️ for developers and creators**

*Last Updated: 2025-11-10*
