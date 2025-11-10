# Creator Automation MVP - Project Plan

**Last Updated:** 2025-11-10
**Status:** Phase 1 - Foundation Setup
**Target Launch:** Week 8 (2025-01-05)

---

## 🎯 Vision

**Product Name:** *TBD* (working name: "DriveEdit" or "CreatorFlow")

**Tagline:** "Drop photos in Google Drive, get pro edits back automatically"

**Target User:** Time-starved indie creators (Instagram influencers, YouTubers, small agencies) who need consistent, professional editing without manual work.

**Core Value Proposition:**
- Upload raw photos to watched Google Drive folder
- System automatically applies professional presets
- Edited photos appear in output folder within 30 seconds
- No manual editing, no learning curve, no software to install

---

## 📊 Success Metrics

### Technical Goals (MVP)
- ✅ Drive file detection: <30 seconds
- ✅ Processing time: <10 seconds per image
- ✅ Success rate: >95%
- ✅ Uptime: >99%

### User Goals (Beta)
- ✅ 10 beta testers recruited
- ✅ 50%+ retention (use 2+ times)
- ✅ 8/10+ preset satisfaction
- ✅ "Would be upset if gone": >70%

### Business Goals (Launch)
- ✅ 100 signups in first week
- ✅ 10%+ free-to-paid conversion
- ✅ $500+ MRR by end of Month 1
- ✅ <10% monthly churn

---

## 🏗️ Architecture Decision

**Decision:** Build on existing `comfy-api-service` repository

**Rationale:**
1. 90% of infrastructure already built and tested
2. Reuse proven ComfyUI integration, job queue, error handling
3. Faster to MVP (4 weeks vs 10 weeks from scratch)
4. Lower costs (one infrastructure, not two)
5. More flexibility (can sell API + Creator tool separately)

**Structure:**
```
comfy-api-service/
├── apps/
│   ├── api/         # EXISTING: API for developers (untouched)
│   ├── creator/     # NEW: Creator automation features
│   ├── worker/      # EXISTING: Extend for Drive jobs
│   └── web/         # NEW: Dashboard UI
├── sdk/             # EXISTING: Keep for API users
├── workflows/       # EXISTING: Extend with presets
└── docker-compose.yml  # EXTENDED: Add Postgres
```

---

## 📅 Timeline & Phases

### **Phase 1: Foundation (Week 1)** ← Current
**Goal:** Set up project structure and storage abstraction

**Tasks:**
- [x] Document project plan (this file)
- [ ] Create `apps/creator/` directory structure
- [ ] Define storage provider abstraction (Drive/MinIO/Dropbox)
- [ ] Update docker-compose.yml (add Postgres)
- [ ] Define database schema (users, subscriptions, jobs)
- [ ] Update ARCHITECTURE.md with decisions

**Deliverable:** Clean foundation for building features

---

### **Phase 2: Google Drive Integration (Week 1-2)**
**Goal:** Core automation - detect files in Drive, process, upload results

**Tasks:**
- [ ] Set up Google Cloud Console project
- [ ] Enable Google Drive API
- [ ] Implement OAuth 2.0 flow (authorization + token refresh)
- [ ] Build Drive folder polling service (cron every 5 min)
- [ ] Implement file download (Drive → temp storage)
- [ ] Implement file upload (result → Drive output folder)
- [ ] Add rate limiting (10K requests/day free tier)
- [ ] Add retry logic (exponential backoff)
- [ ] Test end-to-end with 10 sample images

**Deliverable:** Working Drive automation (manual trigger)

---

### **Phase 3: Image Presets (Week 2)**
**Goal:** Create 3 killer presets that demonstrate value

**Tasks:**
- [ ] Research free LUTs and color grading tutorials
- [ ] Create Preset #1: "Portrait Pro"
  - Skin smoothing, warm tones, soft vignette
- [ ] Create Preset #2: "Product Glow"
  - Clean whites, vibrant colors, sharp details
- [ ] Create Preset #3: "Cinematic"
  - Film grain, teal/orange color grade, contrast
- [ ] Build preset selection router in worker
- [ ] Test each preset with 10+ varied images
- [ ] Create before/after gallery (for marketing)

**Deliverable:** 3 production-ready presets

---

### **Phase 4: Job Queue Enhancement (Week 2-3)**
**Goal:** Extend worker to handle Drive-triggered jobs with metadata

**Tasks:**
- [ ] Extend Dramatiq tasks for Drive processing
- [ ] Add job metadata (user_id, drive_file_id, preset_name)
- [ ] Implement progress tracking (queued → processing → complete)
- [ ] Add error handling for Drive API failures
- [ ] Create job history (last 30 days per user)
- [ ] Test job recovery (worker restart during processing)

**Deliverable:** Robust job processing pipeline

---

### **Phase 5: User Dashboard (Week 3)**
**Goal:** Simple web UI for setup and monitoring

**Tasks:**
- [ ] Create simple HTML/CSS/JS dashboard (no React/Vue)
- [ ] Build OAuth login page ("Connect Google Drive")
- [ ] Add folder selection UI (pick watched folder)
- [ ] Create preset selection interface (3 cards with previews)
- [ ] Build job status page (list recent jobs with progress)
- [ ] Add before/after slider for completed jobs
- [ ] Implement usage tracking (uploads this month / limit)

**Deliverable:** Functional dashboard for user onboarding

---

### **Phase 6: Stripe Integration (Week 3-4)**
**Goal:** Monetization - free tier + paid subscription

**Tasks:**
- [ ] Set up Stripe account
- [ ] Create products (Free: 10/month, Creator: 100/month @ $29)
- [ ] Implement Stripe Checkout (redirect flow)
- [ ] Build webhook handler (subscription.created, payment_failed)
- [ ] Add usage limits (enforce in job queue)
- [ ] Create billing portal (cancel/upgrade subscription)
- [ ] Test full flow (signup → pay → process → cancel)

**Deliverable:** Working payment system

---

### **Phase 7: Landing Page (Week 4)**
**Goal:** Marketing site to drive signups

**Tasks:**
- [ ] Write copy (hero, features, pricing, FAQ)
- [ ] Build landing page (Carrd or custom HTML)
- [ ] Design logo and brand assets (Canva)
- [ ] Create demo video (30-60 sec screen recording)
- [ ] Set up email collection (Mailchimp/ConvertKit)
- [ ] Write 3-5 showcase examples (before/after with story)

**Deliverable:** Public-facing marketing site

---

### **Phase 8: Beta Testing (Week 4-6)**
**Goal:** Validate product-market fit with real users

**Tasks:**
- [ ] Create feedback form (Google Forms)
- [ ] Recruit 10 beta testers (Reddit, X, communities)
- [ ] Send onboarding emails (setup instructions)
- [ ] Monitor usage daily (errors, completion rates)
- [ ] Collect feedback weekly (surveys + 1-on-1 calls)
- [ ] Fix top 3 complaints
- [ ] Iterate on presets based on feedback
- [ ] Measure retention (7-day and 30-day active)

**Deliverable:** Validated MVP with >50% retention

---

### **Phase 9: Launch Prep (Week 6-7)**
**Goal:** Polish and prepare for public launch

**Tasks:**
- [ ] Set up analytics (Plausible or Google Analytics)
- [ ] Add error monitoring (Sentry)
- [ ] Write launch announcements (Product Hunt, Reddit, X)
- [ ] Prepare Product Hunt assets (screenshots, GIFs)
- [ ] Create referral program (refer = 1 month free)
- [ ] Set up support (email + Discord or Telegram)
- [ ] Write launch week content (3-5 social posts)

**Deliverable:** Launch-ready product

---

### **Phase 10: Public Launch (Week 8)**
**Goal:** Get first 100 users

**Tasks:**
- [ ] Launch on Product Hunt (Wednesday)
- [ ] Post to Reddit (r/sidehustle, r/SaaS, r/entrepreneur)
- [ ] Share on X/Twitter with demo
- [ ] Email beta testers for reviews/shares
- [ ] Monitor and respond to comments
- [ ] Track metrics (signups, conversions, MRR)

**Deliverable:** 100+ signups, $500+ MRR

---

### **Phase 11: Post-Launch (Week 8+)**
**Goal:** Optimize and grow

**Tasks:**
- [ ] Analyze conversion funnel
- [ ] A/B test pricing ($19/$29/$39)
- [ ] Optimize landing page
- [ ] Add testimonials
- [ ] Implement watermark feature
- [ ] Track churn and interview churned users
- [ ] Plan next features (video, more presets)

**Deliverable:** Growing, profitable product

---

## 💰 Budget & Costs

### Development Costs (Solo Bootstrap)
- **Week 1-4:** $0-200
  - Domain: $15/year
  - RunPod GPU: $50-100/month (existing)
  - Google Cloud: $0 (free tier)

- **Week 4-6:** $100-500
  - Colorist for 1 preset: $300 (one-time)
  - Designer for landing page: $200 (one-time)

- **Week 6-8:** $200-500
  - Stripe fees: ~3% of revenue
  - Email service: $0-20/month (free tier)
  - Analytics: $0 (Plausible free for <10K views)

**Total MVP Budget:** $500-1,200

### Monthly Operating Costs
```
RunPod GPU: $50-100/month (scale with usage)
Domain + Hosting: $15/month
Email service: $0-20/month
Stripe: 3% of revenue
Total: ~$100/month + 3% revenue
```

### Revenue Projections

**Conservative (10% conversion):**
```
Month 1: 100 signups → 10 paid = $290 MRR
Month 2: 200 total → 20 paid = $580 MRR
Month 3: 350 total → 35 paid = $1,015 MRR
```

**Optimistic (20% conversion):**
```
Month 1: 100 signups → 20 paid = $580 MRR
Month 2: 250 total → 50 paid = $1,450 MRR
Month 3: 500 total → 100 paid = $2,900 MRR
```

**Breakeven:** 20 paying users ($580/month)

---

## 🎯 Pricing Structure

### Free Tier
- 10 image edits per month
- Access to all 3 presets
- Watermarked outputs (small logo)
- Email support (48-hour response)

### Creator Tier - $29/month
- 100 image edits per month
- All presets + priority access to new presets
- No watermark
- Email support (24-hour response)
- Early access to video features

### Studio Tier - $99/month (Future)
- 500 image edits per month
- Custom preset creation
- Video editing (when available)
- Priority processing
- Discord community access
- 1-on-1 onboarding call

---

## 🔒 Risk Mitigation

### Risk 1: Google Drive API Changes
**Probability:** Medium
**Impact:** High (existential threat)

**Mitigation:**
- Build storage provider abstraction from Day 1
- Add Dropbox support in Phase 2 (Month 2)
- Offer MinIO self-hosted option for agencies
- Monitor Google announcements closely

### Risk 2: Poor Preset Quality
**Probability:** Medium
**Impact:** High (kills retention)

**Mitigation:**
- Beta test with 10+ users before launch
- Iterate based on feedback (weekly updates)
- Hire professional colorist for at least 1 preset ($300)
- Build preset rating system (track favorites)

### Risk 3: Low Conversion Rate
**Probability:** Medium
**Impact:** Medium (slower growth)

**Mitigation:**
- A/B test pricing ($19/$29/$39)
- Offer annual plans (2 months free)
- Add referral incentives
- Improve onboarding (reduce friction)
- Add social proof (testimonials, case studies)

### Risk 4: Competitors Copy
**Probability:** High
**Impact:** Medium

**Mitigation:**
- Build preset marketplace (network effects)
- Focus on execution speed (ship fast)
- Create community (Discord, shared presets)
- Develop brand loyalty (personal touch)

### Risk 5: Solo Burnout
**Probability:** Medium
**Impact:** High

**Mitigation:**
- Work in 2-week sprints with 1-week breaks
- Outsource design/presets ($500 budget)
- Join founder communities (accountability)
- Set "quit trigger" (if <10 users after 2 months, pivot)

---

## 📝 Decision Log

### 2025-11-10: Build on Existing API
**Decision:** Extend `comfy-api-service` instead of starting new project

**Reasons:**
1. 90% of infrastructure already built
2. Proven ComfyUI integration
3. 4 weeks to MVP vs 10 weeks new build
4. Lower costs and complexity

**Trade-offs:**
- Need to maintain clean separation (API vs Creator routes)
- Slightly more complex codebase
- But: worth it for speed and cost savings

### 2025-11-10: Images-Only MVP
**Decision:** Focus on image editing, defer video to Phase 2

**Reasons:**
1. ComfyUI excels at images
2. Faster iteration (2s vs 30s processing)
3. Simpler workflows (no audio sync, codecs)
4. Creators need photo editing too (thumbnails, IG)

**Trade-offs:**
- Smaller initial market (excludes video-only creators)
- But: easier to prove value and iterate

### 2025-11-10: Polling vs Webhooks
**Decision:** Start with polling (every 5 min), upgrade to webhooks later

**Reasons:**
1. Polling is simpler to implement
2. No webhook infrastructure needed
3. 5-min delay acceptable for MVP
4. Can upgrade to real-time later

**Trade-offs:**
- 5-min detection delay
- But: much faster to ship

---

## 📚 Reference Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [CREATOR_FEATURES.md](CREATOR_FEATURES.md) - Feature specifications
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - DB design
- [API_INTEGRATION.md](API_INTEGRATION.md) - How API and Creator coexist
- [PRESET_GUIDE.md](PRESET_GUIDE.md) - Preset creation guide
- [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) - Pre-launch tasks

---

## 🎯 Current Status

**Week:** 1
**Phase:** Foundation Setup
**Next Milestone:** Complete Phase 1 by end of Week 1

**Completed:**
- [x] Project plan documented
- [x] Todo list created
- [x] Architecture decision made

**In Progress:**
- [ ] Creating creator app structure
- [ ] Defining storage abstraction

**Blocked:** None

**Next Session:**
1. Create `apps/creator/` directory structure
2. Define storage provider interfaces
3. Update docker-compose.yml with Postgres
4. Document database schema

---

*This is a living document. Update after each major milestone or decision.*
