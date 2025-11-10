# Shared Documentation

Documentation relevant to **both API and Creator products**.

---

## 📚 Documentation

### Business & Strategy
- **[BUSINESS_MODEL.md](BUSINESS_MODEL.md)** - Monetization strategy
  - Competitor analysis (Descript, Replicate, Stability AI)
  - Pricing models (usage-based, subscription, hybrid)
  - Target customers and segments
  - Revenue projections
  - Go-to-market strategy

- **[USER_EXPERIENCE_GUIDE.md](USER_EXPERIENCE_GUIDE.md)** - How users interact
  - Complete user workflows
  - API parameters and options
  - Real-world use cases
  - Dashboard mockups

### Technical Architecture
- **[API_INTEGRATION.md](API_INTEGRATION.md)** - How API + Creator coexist
  - Routing strategy (separate routes, shared backend)
  - Authentication (API Key vs OAuth)
  - Shared services (ComfyUI, storage)
  - Deployment architecture
  - Database strategy

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────┐
│       FastAPI Application (Port 8000)           │
│                                                 │
│  ┌────────────┐              ┌──────────────┐  │
│  │ API Routes │              │Creator Routes│  │
│  │ /api/v1/*  │              │ /creator/*   │  │
│  │            │              │              │  │
│  │Auth: API   │              │Auth: OAuth   │  │
│  │     Key    │              │              │  │
│  └─────┬──────┘              └──────┬───────┘  │
└────────┼──────────────────────────┼────────────┘
         │                          │
         ▼                          ▼
   ┌──────────────────────────────────────┐
   │      Shared Services Layer           │
   │  - ComfyUI Client                    │
   │  - Storage Providers                 │
   │  - Job Queue (Dramatiq + Redis)      │
   └──────────────────────────────────────┘
```

**Key Insight:** Two products, one backend. Clean separation via routing, shared infrastructure for efficiency.

---

## 🎯 Product Comparison

| Aspect | API Product | Creator Product |
|--------|-------------|-----------------|
| **Target** | Developers | End Users |
| **Auth** | API Key | OAuth + Session |
| **Pricing** | Usage-based | Subscription |
| **Storage** | MinIO | Google Drive |
| **Routes** | `/api/v1/*` | `/creator/*` |
| **Database** | Redis only | Postgres + Redis |

---

## 🔗 Related Documentation

- [API Product Docs](../api/) - Developer API documentation
- [Creator Product Docs](../creator/) - End-user automation
- [Main README](../../README.md) - Project overview

---

*Last Updated: 2025-11-10*
