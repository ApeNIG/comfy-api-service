# Quick Start - Building the Creator MVP

**Last Updated:** 2025-11-10

This is your action checklist. Follow this sequence to build the MVP efficiently.

---

## 📚 Documentation Created

✅ **Core Planning Docs:**
- [MVP_PROJECT_PLAN.md](MVP_PROJECT_PLAN.md) - Complete project roadmap, timeline, budget
- [CREATOR_FEATURES.md](CREATOR_FEATURES.md) - Feature specs, user flows, presets
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Complete database design
- [API_INTEGRATION.md](API_INTEGRATION.md) - How API + Creator coexist

**Read these first to understand the full vision.**

---

## 🎯 Current Status

**Week:** 1
**Phase:** Foundation Setup
**Next Milestone:** Complete Phase 1 by end of Week 1

---

## ✅ Week 1 Checklist (Foundation)

### Day 1-2: Project Structure

- [ ] **Create directory structure**
  ```bash
  mkdir -p apps/creator/{routers,models,services/storage}
  mkdir -p apps/shared/services
  mkdir -p apps/web/{static/{css,js,images},templates}
  mkdir -p apps/worker/presets
  mkdir -p alembic/versions
  ```

- [ ] **Define storage abstraction**
  - Create `apps/shared/services/storage.py` (StorageProvider ABC)
  - Create `apps/creator/services/storage/drive.py` (GoogleDriveProvider)
  - Create `apps/creator/services/storage/minio.py` (MinIOProvider)

- [ ] **Update docker-compose.yml**
  - Add Postgres service
  - Add environment variables for Creator features
  - Test with `docker-compose up -d postgres`

- [ ] **Set up database**
  - Install Alembic: `pip install alembic psycopg2-binary`
  - Initialize: `alembic init alembic`
  - Create initial migration
  - Run migration: `alembic upgrade head`

- [ ] **Update ARCHITECTURE.md**
  - Document storage abstraction decisions
  - Update system diagram with Creator components

---

### Day 3-4: Google Drive Integration Basics

- [ ] **Google Cloud Console setup**
  - Create new project: "CreatorFlow" or similar
  - Enable Google Drive API
  - Create OAuth credentials (Web application)
  - Set redirect URI: `http://localhost:8000/creator/auth/callback`
  - Save Client ID and Secret to `.env`

- [ ] **Install dependencies**
  ```bash
  pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
  ```

- [ ] **Implement OAuth flow**
  - Create `apps/creator/routers/auth.py`
  - `/auth/login` - Redirect to Google
  - `/auth/callback` - Handle OAuth callback
  - Save tokens to database (encrypted)

- [ ] **Test OAuth**
  - Run API: `uvicorn apps.main:app --reload`
  - Visit: `http://localhost:8000/creator/auth/login`
  - Authorize and verify callback works
  - Check database has user + tokens

---

### Day 5-7: Drive File Operations

- [ ] **Implement Drive service**
  - Create `apps/creator/services/storage/drive.py`
  - Method: `list_files(folder_id)` - List files in folder
  - Method: `download_file(file_id)` - Download file bytes
  - Method: `upload_file(bytes, folder_id, filename)` - Upload file

- [ ] **Folder management**
  - Create `apps/creator/routers/drive.py`
  - `/drive/folders` - List user's Drive folders
  - `/drive/watch` - Set watched folder
  - Auto-create "Edited" subfolder

- [ ] **Test manually**
  - Upload test image to Drive
  - Call `/drive/folders` - verify it appears
  - Call download method - verify file downloads
  - Call upload method - verify file uploads to Drive

---

## 🎯 Week 2 Checklist (Processing)

### Day 8-10: Image Presets

- [ ] **Research presets**
  - Find free LUTs (search: "free cinematic LUT download")
  - Watch YouTube tutorials on color grading
  - Collect sample images for testing

- [ ] **Create Portrait Pro preset**
  - File: `apps/worker/presets/portrait_pro.json`
  - Effects: Skin smoothing, warm tones, vignette
  - Test with 10 portrait photos
  - Iterate until 8/10 quality

- [ ] **Create Product Glow preset**
  - File: `apps/worker/presets/product_glow.json`
  - Effects: White background, vibrant colors
  - Test with 10 product photos

- [ ] **Create Cinematic preset**
  - File: `apps/worker/presets/cinematic.json`
  - Effects: Teal/orange grade, film grain
  - Test with 10 landscape/travel photos

- [ ] **Build preset loader**
  - Create `apps/shared/services/presets.py`
  - Function: `load_preset(name)` returns workflow JSON
  - Cache presets in memory

---

### Day 11-14: Job Queue Integration

- [ ] **Extend worker tasks**
  - Update `apps/worker/tasks.py`
  - Add `drive_process_upload` actor
  - Implement: Download → Process → Upload flow

- [ ] **Add job tracking**
  - Update jobs table with Creator fields
  - Track Drive file IDs
  - Track preset used
  - Store processing time

- [ ] **Build polling service**
  - Create `apps/worker/poller.py`
  - Cron job (every 5 min)
  - Check each user's watched folder
  - Enqueue jobs for new files

- [ ] **Test end-to-end**
  - Upload image to watched folder
  - Wait 5 minutes
  - Verify job created
  - Verify image processed
  - Verify output in Drive

---

## 🎯 Week 3 Checklist (Dashboard)

### Day 15-17: Basic UI

- [ ] **Create dashboard HTML**
  - File: `apps/web/templates/dashboard.html`
  - Sections: Header, stats, recent jobs
  - Simple CSS (no frameworks)
  - Mobile-responsive

- [ ] **Implement dashboard API**
  - File: `apps/creator/routers/dashboard.py`
  - `/dashboard/stats` - Usage this month
  - `/dashboard/jobs` - Recent jobs (last 30)

- [ ] **Add preset selection**
  - UI: 3 cards with before/after previews
  - API: `/presets/select` - Set default preset
  - Save to user preferences

---

### Day 18-21: Billing Integration

- [ ] **Set up Stripe**
  - Create Stripe account
  - Create products:
    - Free: $0 (10 images/month)
    - Creator: $29/month (100 images)
  - Save API keys to `.env`

- [ ] **Implement Stripe Checkout**
  - File: `apps/creator/routers/billing.py`
  - `/billing/checkout` - Create checkout session
  - Redirect to Stripe
  - Handle success/cancel

- [ ] **Webhook handler**
  - `/billing/webhook` - Stripe webhook endpoint
  - Handle: `customer.subscription.created`
  - Handle: `customer.subscription.deleted`
  - Update subscription in database

- [ ] **Test payment flow**
  - Use Stripe test mode
  - Complete checkout
  - Verify subscription created
  - Test webhook events

---

## 🎯 Week 4 Checklist (Polish)

### Day 22-24: Landing Page

- [ ] **Write copy**
  - Hero: "Drop photos in Drive, get pro edits back"
  - Features: 3-4 key benefits
  - Pricing: Free vs Creator tiers
  - FAQ: 5-7 common questions

- [ ] **Build landing page**
  - Option A: Use Carrd ($19/year)
  - Option B: Custom HTML in `apps/web/`
  - Include email signup form

- [ ] **Create demo video**
  - Record: Upload → Process → Download flow
  - 30-60 seconds
  - Add to landing page
  - Upload to YouTube

---

### Day 25-28: Beta Testing Prep

- [ ] **Create feedback form**
  - Use Google Forms
  - Questions:
    - How easy was setup? (1-10)
    - Preset quality? (1-10)
    - What would you change?
    - Would you pay $29/month?

- [ ] **Write onboarding email**
  - Welcome message
  - Setup instructions (3-5 steps)
  - Link to demo video
  - Link to feedback form

- [ ] **Recruit beta testers**
  - Post to r/sidehustle: "Free AI photo editor beta"
  - Post to r/instagram: "Auto-edit photos with AI"
  - Goal: 10 signups

- [ ] **Set up support**
  - Create support email
  - Or: Discord server for beta testers
  - Respond within 24 hours

---

## 🎯 Weeks 5-6 (Beta Testing)

- [ ] Send onboarding emails
- [ ] Monitor usage daily
- [ ] Fix bugs as they arise
- [ ] Collect feedback weekly
- [ ] Iterate on presets
- [ ] Measure retention
- [ ] Interview 3-5 users (video calls)
- [ ] Identify top 3 complaints
- [ ] Fix complaints before launch

**Success Criteria:**
- 50%+ use it more than once
- 8/10+ average preset rating
- 70%+ "would be upset if gone"

---

## 🎯 Weeks 7-8 (Launch)

### Week 7: Prep

- [ ] Set up analytics
- [ ] Set up error monitoring (Sentry)
- [ ] Write Product Hunt post
- [ ] Create PH assets (screenshots, GIFs)
- [ ] Write launch tweets
- [ ] Create referral program
- [ ] Final bug fixes

### Week 8: Launch

- [ ] **Wednesday:** Launch on Product Hunt
- [ ] Post to Reddit (5+ communities)
- [ ] Tweet launch announcement
- [ ] Email beta testers for reviews
- [ ] Monitor comments/feedback
- [ ] Track signups, conversions, MRR
- [ ] Fix critical bugs immediately

**Goal:** 100 signups, 10 paid users, $290 MRR

---

## 🚨 Common Pitfalls to Avoid

1. **Perfectionism** - Ship 80% solution, iterate
2. **Scope creep** - Stick to 3 presets, defer video
3. **Over-engineering** - No React, no microservices
4. **Ignoring users** - Beta feedback is gold
5. **Poor presets** - Quality here = retention
6. **Weak onboarding** - Make setup < 5 minutes
7. **No analytics** - Track everything from Day 1

---

## 📊 Success Metrics to Track

**Weekly:**
- Active users (7-day)
- Jobs processed
- Error rate
- Average processing time

**Monthly:**
- Signups
- Free → Paid conversion
- Churn rate
- MRR
- NPS score

**Use a spreadsheet or Notion database.**

---

## 🆘 Stuck? Do This

1. **Check docs** - Re-read relevant .md file
2. **Simplify** - Can you ship 50% solution today?
3. **Ask for help** - Reddit, Discord, founder communities
4. **Take a break** - Walk, sleep, come back fresh
5. **Remember why** - You're solving a real problem

---

## 🎯 Next Session

Ready to start building? Here's what we'll do:

1. Create directory structure
2. Define storage abstraction
3. Update docker-compose.yml
4. Set up Postgres database

**Estimated time:** 2-3 hours

---

**Let's build this! 🚀**
