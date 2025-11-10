# Creator Automation - Feature Specifications

**Last Updated:** 2025-11-10

---

## 🎯 Core User Flow

### The Magic Workflow

```
1. User signs up → Connects Google Drive (OAuth)
2. Selects watched folder (e.g., "Raw Photos")
3. Chooses default preset (e.g., "Portrait Pro")
4. System creates output folder ("Edited Photos")

5. User uploads photo to "Raw Photos" from phone/computer
6. Within 5 minutes, system detects new file
7. Downloads image, applies preset, uploads to "Edited Photos"
8. User gets email: "Your photo is ready!"
9. Opens Drive, downloads edited photo, posts to Instagram

Time saved: 15-30 minutes per photo
```

---

## 🔐 Authentication & Authorization

### User Registration
- **Method:** Google OAuth 2.0 only (no email/password)
- **Flow:**
  1. Click "Connect Google Drive"
  2. Authorize Drive access (read/write to selected folder only)
  3. User record created in database
  4. Redirect to dashboard

### Permissions Requested
- `https://www.googleapis.com/auth/drive.file` - Access only files created by app
- `https://www.googleapis.com/auth/drive.metadata.readonly` - Read folder structure

**Why minimal permissions:** Builds trust, reduces security concerns

### Token Management
- Access tokens stored encrypted in database
- Refresh tokens used for long-term access
- Tokens refreshed automatically before expiry
- User can revoke access anytime (OAuth settings page)

---

## 📁 Storage Integration

### Google Drive Provider

**Watched Folder Setup:**
- User selects existing folder or creates new one
- System creates subfolder structure:
  ```
  My Drive/
  └── CreatorFlow/
      ├── Raw/          ← User uploads here
      └── Edited/       ← System outputs here
  ```

**Polling Mechanism:**
- Cron job runs every 5 minutes
- Checks for files modified since last poll
- Filters: images only (.jpg, .jpeg, .png, .webp)
- Tracks processed files to avoid duplicates

**File Processing:**
1. Detect new file in Raw folder
2. Create job record in database
3. Download to temp storage (`/tmp/`)
4. Process with ComfyUI
5. Upload result to Edited folder
6. Delete temp files
7. Mark job complete

**Rate Limiting:**
- Google Drive API: 10,000 requests/day (free)
- Our usage: ~2,880 polls/day (every 5 min)
- Safety margin: 70% headroom for user files

### MinIO Fallback (Future)
- For users who want self-hosted option
- Same interface, different provider
- Useful for agencies with compliance needs

---

## 🎨 Preset System

### MVP Presets (3 Total)

#### 1. Portrait Pro
**Target Use Case:** Instagram selfies, headshots, portrait photography

**Effects:**
- Skin smoothing (subtle, not fake)
- Warm color temperature (+200K)
- Soft vignette (80% opacity)
- Slight contrast boost (+15%)
- Sharpen eyes and lips
- Reduce blemishes

**Before/After Example:**
- Before: Smartphone selfie, harsh lighting, visible pores
- After: Professional headshot look, smooth skin, warm glow

**Technical Implementation:**
- ComfyUI workflow: `workflows/presets/portrait_pro.json`
- Models: Stable Diffusion inpainting for blemishes
- Post-processing: PIL for vignette, color adjustment

---

#### 2. Product Glow
**Target Use Case:** E-commerce, product photography, Instagram shop posts

**Effects:**
- Pure white background (255, 255, 255)
- Vibrant color saturation (+25%)
- Sharp details (unsharp mask)
- Soft shadow under product
- Remove distractions/clutter

**Before/After Example:**
- Before: Product photo on cluttered table
- After: Clean studio shot with white background

**Technical Implementation:**
- Background removal: rembg or ComfyUI SAM
- Color boost: Saturation adjustment
- Shadow: Synthetic shadow generation

---

#### 3. Cinematic
**Target Use Case:** Travel vlogs, YouTube thumbnails, storytelling photos

**Effects:**
- Teal/orange color grade (film look)
- Film grain texture (ISO 800 equivalent)
- Crushed blacks (15 IRE floor)
- Anamorphic letterbox bars (optional)
- Slight desaturation (80%)

**Before/After Example:**
- Before: Flat smartphone photo of sunset
- After: Cinematic film still with mood

**Technical Implementation:**
- LUT application: Free "Teal/Orange" LUT
- Grain: Overlay texture
- Letterbox: PIL drawing

---

### Preset Selection

**User Interface:**
```
┌─────────────────────────────────────────────┐
│  Choose Your Style                          │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │ Before  │  │ Before  │  │ Before  │    │
│  │  ↓      │  │  ↓      │  │  ↓      │    │
│  │ After   │  │ After   │  │ After   │    │
│  │         │  │         │  │         │    │
│  │Portrait │  │ Product │  │Cinematic│    │
│  │  Pro    │  │  Glow   │  │         │    │
│  └─────────┘  └─────────┘  └─────────┘    │
│     [✓]          [ ]          [ ]          │
│  Best for:    Best for:    Best for:      │
│  Selfies      Products     Travel         │
│  Headshots    Shops        Thumbnails     │
└─────────────────────────────────────────────┘
```

**Behavior:**
- User picks one preset as default
- Can override per-folder (e.g., "Products" folder → Product Glow)
- Can change default anytime

---

## 💼 Job Management

### Job Lifecycle

```
┌─────────┐
│ QUEUED  │  ← File detected, job created
└────┬────┘
     ↓
┌─────────┐
│PROCESSING│ ← Worker downloaded file, started ComfyUI
└────┬────┘
     ↓
┌─────────┐
│COMPLETED│  ← Result uploaded to Drive, user notified
└────┬────┘
     ↓
┌─────────┐
│ ARCHIVED│  ← After 30 days (for free tier)
└─────────┘
```

**Error States:**
- `FAILED` - Processing error, user can retry
- `CANCELLED` - User manually cancelled
- `RATE_LIMITED` - Hit monthly limit

### Job Metadata

Stored in Postgres:
```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    status VARCHAR(20),

    -- Drive info
    drive_file_id VARCHAR(255),
    drive_file_name VARCHAR(500),
    drive_folder_id VARCHAR(255),

    -- Processing
    preset_name VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Result
    output_drive_file_id VARCHAR(255),
    output_url TEXT,

    -- Errors
    error_message TEXT,
    retry_count INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW()
);
```

### Job History

**User Dashboard:**
- Shows last 30 days of jobs
- Filters: All, Completed, Failed
- Sortable by date
- Click to view before/after

**Display:**
```
┌──────────────────────────────────────────────┐
│  Recent Edits                                │
├──────────────────────────────────────────────┤
│  ✓ sunset.jpg → Cinematic    2 hours ago    │
│  ✓ product-1.jpg → Product   4 hours ago    │
│  ✗ selfie.jpg → Portrait     Yesterday       │
│     Error: File too large                    │
│  ✓ headshot.jpg → Portrait   2 days ago     │
└──────────────────────────────────────────────┘
```

---

## 📊 Usage Tracking & Limits

### Tier Limits

| Tier | Monthly Limit | Overage |
|------|--------------|---------|
| Free | 10 images | Blocked until next month |
| Creator ($29) | 100 images | Allowed, pay $0.50/image |
| Studio ($99) | 500 images | Allowed, pay $0.30/image |

### Tracking

**Database:**
```sql
CREATE TABLE usage (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    month DATE,  -- e.g., 2025-11-01
    images_processed INT DEFAULT 0,
    tier VARCHAR(20),
    updated_at TIMESTAMP
);
```

**Reset Logic:**
- Resets on 1st of each month
- Subscription renewal date (for paid users)

**UI Display:**
```
┌─────────────────────────────┐
│  Usage This Month           │
├─────────────────────────────┤
│  ████████░░  80/100         │
│                             │
│  20 remaining               │
│  Resets in 12 days          │
│                             │
│  [Upgrade to Studio]        │
└─────────────────────────────┘
```

### Overage Handling

**Creator Tier:** Auto-charge $0.50 per image over limit
**Free Tier:** Show upgrade prompt, block processing

---

## 🔔 Notifications

### Email Notifications

**Triggers:**
1. **Job Complete** - "Your photo is ready!"
   - Subject: "✅ sunset.jpg edited with Cinematic preset"
   - Body: Link to Drive folder, before/after preview

2. **Job Failed** - "Editing failed"
   - Subject: "❌ selfie.jpg couldn't be processed"
   - Body: Error reason, troubleshooting link

3. **Limit Warning** - "90% of monthly quota used"
   - Subject: "⚠️ You've used 90 of 100 edits this month"
   - Body: Usage stats, upgrade CTA

4. **Payment Failed** - "Update your payment method"
   - Subject: "🔴 Payment failed - Update card"
   - Body: Link to billing portal

**Frequency Limits:**
- Max 1 email per hour (batched updates)
- User can disable notifications (keep critical ones)

### In-App Notifications

**Dashboard Bell Icon:**
- Real-time via WebSocket
- Shows recent activity
- Click to view job details

---

## 🎨 Dashboard UI

### Pages

#### 1. Home / Dashboard
- Usage stats (this month)
- Recent jobs (last 10)
- Quick actions (upload, change preset)

#### 2. Settings
- Connected folders
- Default preset selection
- Notification preferences
- Billing (for paid users)

#### 3. Billing
- Current plan
- Usage history
- Invoices
- Upgrade/downgrade
- Cancel subscription

#### 4. Help
- Quick start guide
- FAQs
- Contact support
- Community Discord link

### Design Principles

**Keep It Simple:**
- No frameworks (vanilla JS)
- Fast loading (<1s)
- Mobile-responsive
- Clean, minimal design

**Inspiration:**
- Stripe Dashboard (clean, data-focused)
- Notion (simple, intuitive)
- Linear (fast, keyboard shortcuts)

---

## 🔒 Security & Privacy

### Data Protection

**Encrypted at Rest:**
- User OAuth tokens (AES-256)
- Payment info (Stripe handles, we don't store)

**Encrypted in Transit:**
- HTTPS only (no HTTP)
- Secure WebSocket (WSS)

**Temporary Files:**
- Deleted immediately after processing
- Max retention: 1 hour (cleanup job)

**Access Control:**
- Users can only see their own jobs
- Admin access logged and auditable

### Privacy Policy (Summary)

**We collect:**
- Google account email (for login)
- Drive folder IDs (for watching)
- Processed images (temporarily, deleted after upload)
- Usage stats (anonymized)

**We don't:**
- Sell data to third parties
- Train AI on your images
- Access files outside watched folders
- Store payment info (Stripe handles)

**You can:**
- Delete account anytime (all data purged)
- Export job history
- Revoke Drive access
- Request data deletion (GDPR)

---

## 🚀 Future Features (Post-MVP)

### Phase 2 Features (Month 2-3)

1. **Video Support**
   - Auto-captions (Whisper API)
   - Color grading (same presets)
   - Auto-crop to 9:16 (Reels/Shorts)

2. **Preset Marketplace**
   - User-created presets
   - Revenue share (70/30)
   - Ratings and reviews

3. **Reference Style Upload**
   - Upload example image
   - Extract style with CLIP
   - Apply to new images

4. **Batch Processing**
   - Upload multiple files
   - Process all with same preset
   - Download as ZIP

5. **Dropbox Integration**
   - Alternative to Google Drive
   - Same polling mechanism

### Phase 3 Features (Month 4-6)

1. **Mobile App** (Maybe)
   - Direct upload from phone
   - Push notifications
   - Quick preview

2. **API Access** (For Creator Tier)
   - REST API for automation
   - Webhooks for job updates
   - SDK (Python, JS)

3. **Team Plans**
   - Shared folders
   - Multiple users
   - Usage pooling

4. **Advanced Presets**
   - ControlNet (pose, depth)
   - Inpainting (object removal)
   - Upscaling (2x, 4x)

---

## 📈 Success Metrics

### Health Metrics

**Technical:**
- Job success rate: >95%
- Average processing time: <10s
- Drive polling accuracy: >99%
- Uptime: >99.5%

**User:**
- 7-day retention: >50%
- 30-day retention: >30%
- NPS score: >50
- Support tickets per user: <0.1

**Business:**
- Free → Paid conversion: >10%
- Monthly churn: <10%
- LTV:CAC ratio: >3:1
- MRR growth: >20% month-over-month

---

*This document will be updated as features evolve based on user feedback.*
