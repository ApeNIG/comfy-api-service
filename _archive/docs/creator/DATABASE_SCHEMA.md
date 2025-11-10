# Database Schema - Creator Automation

**Last Updated:** 2025-11-10
**Database:** PostgreSQL 15

---

## 📊 Schema Overview

```
┌─────────┐       ┌──────────────┐       ┌──────┐
│  users  │──────▶│subscriptions │──────▶│ jobs │
└─────────┘       └──────────────┘       └──────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ usage_tracking  │
                  └─────────────────┘
```

---

## 🗃️ Tables

### `users`
Core user accounts and authentication.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- OAuth / Auth
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,

    -- Drive Integration
    drive_access_token TEXT,  -- Encrypted
    drive_refresh_token TEXT,  -- Encrypted
    drive_token_expires_at TIMESTAMP,
    watched_folder_id VARCHAR(255),
    output_folder_id VARCHAR(255),

    -- Preferences
    default_preset VARCHAR(50) DEFAULT 'portrait_pro',
    email_notifications BOOLEAN DEFAULT TRUE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
```

**Notes:**
- `drive_access_token` and `drive_refresh_token` stored encrypted using `pgcrypto`
- `watched_folder_id` is the Drive folder ID user selected
- `output_folder_id` created automatically (subfolder of watched)

---

### `subscriptions`
User subscription and billing status.

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Stripe
    stripe_customer_id VARCHAR(255) UNIQUE,
    stripe_subscription_id VARCHAR(255) UNIQUE,

    -- Plan
    tier VARCHAR(20) NOT NULL DEFAULT 'free',  -- free, creator, studio
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, cancelled, past_due, trialing

    -- Limits
    monthly_limit INT NOT NULL DEFAULT 10,  -- Images per month

    -- Billing
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer_id ON subscriptions(stripe_customer_id);
CREATE UNIQUE INDEX idx_subscriptions_one_per_user ON subscriptions(user_id);
```

**Notes:**
- One subscription per user (enforced by unique index)
- Free tier gets subscription record too (for consistency)
- `tier` determines monthly_limit:
  - `free`: 10 images
  - `creator`: 100 images
  - `studio`: 500 images

---

### `jobs`
Image processing jobs.

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    -- queued, processing, completed, failed, cancelled

    -- Input
    drive_file_id VARCHAR(255) NOT NULL,
    drive_file_name VARCHAR(500) NOT NULL,
    drive_folder_id VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    file_mime_type VARCHAR(100),

    -- Processing
    preset_name VARCHAR(50) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_time_ms INT,  -- For analytics

    -- Output
    output_drive_file_id VARCHAR(255),
    output_file_name VARCHAR(500),
    output_url TEXT,  -- Drive share link

    -- Errors
    error_code VARCHAR(50),
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,

    -- Metadata
    comfyui_prompt_id VARCHAR(255),  -- For debugging
    worker_id VARCHAR(100),  -- Which worker processed

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_user_status ON jobs(user_id, status);
CREATE INDEX idx_jobs_drive_file_id ON jobs(drive_file_id);
```

**Notes:**
- `drive_file_id` is Google Drive's unique file identifier
- `processing_time_ms` used for performance monitoring
- `retry_count` incremented on failure, max 3 attempts
- Old jobs (>90 days) archived to separate table

---

### `usage_tracking`
Monthly usage per user.

```sql
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Period
    month DATE NOT NULL,  -- First day of month, e.g., 2025-11-01

    -- Usage
    images_processed INT DEFAULT 0,
    images_failed INT DEFAULT 0,
    images_overage INT DEFAULT 0,  -- Above monthly limit

    -- Billing
    tier VARCHAR(20) NOT NULL,  -- Snapshot at time
    monthly_limit INT NOT NULL,
    overage_charged_cents INT DEFAULT 0,  -- $0.50 per image = 50 cents

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint: one record per user per month
    UNIQUE(user_id, month)
);

-- Indexes
CREATE INDEX idx_usage_user_month ON usage_tracking(user_id, month);
CREATE INDEX idx_usage_month ON usage_tracking(month);
```

**Notes:**
- Reset on 1st of each month (or subscription renewal date)
- `overage_charged_cents` for Creator tier only
- Free tier blocks at limit, no overage

---

### `drive_polls`
Track Drive folder polling to avoid duplicates.

```sql
CREATE TABLE drive_polls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Polling
    folder_id VARCHAR(255) NOT NULL,
    last_poll_at TIMESTAMP NOT NULL,
    last_modified_time TIMESTAMP,  -- From Drive API
    files_found INT DEFAULT 0,

    -- Status
    poll_status VARCHAR(20) DEFAULT 'success',  -- success, error, rate_limited
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_drive_polls_user_id ON drive_polls(user_id);
CREATE INDEX idx_drive_polls_folder_id ON drive_polls(folder_id);
CREATE INDEX idx_drive_polls_last_poll ON drive_polls(last_poll_at);
```

**Notes:**
- One record per user's watched folder
- `last_modified_time` from Drive API prevents processing same files twice
- `poll_status` for debugging rate limits

---

### `presets`
User-created or shared presets (Future: Marketplace).

```sql
CREATE TABLE presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Preset Data
    workflow_json JSONB NOT NULL,  -- ComfyUI workflow
    thumbnail_url TEXT,
    category VARCHAR(50),  -- portrait, product, landscape, etc.

    -- Marketplace
    is_public BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    price_cents INT DEFAULT 0,  -- $5 = 500 cents
    downloads INT DEFAULT 0,
    rating_avg DECIMAL(3,2) DEFAULT 0.0,  -- 0.00 to 5.00
    rating_count INT DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_presets_created_by ON presets(created_by_user_id);
CREATE INDEX idx_presets_category ON presets(category);
CREATE INDEX idx_presets_public ON presets(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_presets_rating ON presets(rating_avg DESC);
```

**Notes:**
- MVP starts with 3 system presets (created_by_user_id = NULL)
- Phase 2: Users can create/share presets
- `workflow_json` stores full ComfyUI graph
- Rating system for marketplace quality

---

### `webhook_events`
Stripe webhook events log (for debugging).

```sql
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Event
    event_id VARCHAR(255) UNIQUE NOT NULL,  -- Stripe event ID
    event_type VARCHAR(100) NOT NULL,  -- e.g., customer.subscription.created

    -- Payload
    payload JSONB NOT NULL,  -- Full webhook payload

    -- Processing
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_webhook_events_event_type ON webhook_events(event_type);
CREATE INDEX idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX idx_webhook_events_created_at ON webhook_events(created_at);
```

**Notes:**
- Stores all Stripe webhooks for audit trail
- Idempotency: `event_id` unique prevents duplicate processing
- Payload stored for debugging failed webhooks

---

## 🔐 Encryption

### Sensitive Fields

**Encrypted at Rest (using `pgcrypto`):**
```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Example: Encrypt Drive tokens
UPDATE users
SET drive_access_token = pgp_sym_encrypt(
    'actual_token_value',
    current_setting('app.encryption_key')
);

-- Decrypt when reading
SELECT pgp_sym_decrypt(
    drive_access_token::bytea,
    current_setting('app.encryption_key')
) FROM users WHERE id = '...';
```

**Encryption Key:**
- Stored in environment variable `ENCRYPTION_KEY`
- Not in database or code
- Rotated annually

---

## 🗑️ Data Retention

### Cleanup Jobs

**Old Jobs (>90 days):**
```sql
-- Archive to cold storage (separate table)
INSERT INTO jobs_archive SELECT * FROM jobs
WHERE created_at < NOW() - INTERVAL '90 days';

DELETE FROM jobs WHERE created_at < NOW() - INTERVAL '90 days';
```

**Old Usage Tracking (>12 months):**
```sql
DELETE FROM usage_tracking
WHERE month < NOW() - INTERVAL '12 months';
```

**Old Webhook Events (>30 days):**
```sql
DELETE FROM webhook_events
WHERE created_at < NOW() - INTERVAL '30 days';
```

**Schedule:**
- Daily cleanup job (cron)
- Runs at 2 AM UTC

---

## 📈 Analytics Queries

### Monthly Active Users
```sql
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(DISTINCT user_id) AS active_users
FROM jobs
WHERE status = 'completed'
GROUP BY month
ORDER BY month DESC;
```

### User Retention
```sql
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('month', created_at) AS cohort_month
    FROM users
)
SELECT
    c.cohort_month,
    COUNT(DISTINCT c.user_id) AS cohort_size,
    COUNT(DISTINCT CASE WHEN j.created_at >= c.cohort_month + INTERVAL '1 month'
          THEN j.user_id END) AS retained_month_1
FROM cohorts c
LEFT JOIN jobs j ON c.user_id = j.user_id
GROUP BY c.cohort_month
ORDER BY c.cohort_month DESC;
```

### Revenue by Tier
```sql
SELECT
    tier,
    COUNT(*) AS subscribers,
    CASE
        WHEN tier = 'creator' THEN COUNT(*) * 29
        WHEN tier = 'studio' THEN COUNT(*) * 99
        ELSE 0
    END AS monthly_revenue
FROM subscriptions
WHERE status = 'active'
GROUP BY tier;
```

### Processing Performance
```sql
SELECT
    preset_name,
    COUNT(*) AS total_jobs,
    AVG(processing_time_ms) AS avg_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) AS p95_time_ms
FROM jobs
WHERE status = 'completed'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY preset_name;
```

---

## 🚀 Migrations

### Initial Schema
```bash
# Run migrations
alembic upgrade head

# Create first migration
alembic revision -m "initial schema"
```

### Migration Files
Located in `alembic/versions/`

**Example Migration:**
```python
# alembic/versions/001_initial_schema.py
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('google_id', sa.String(255), nullable=False),
        # ... rest of columns
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('google_id')
    )

def downgrade():
    op.drop_table('users')
```

---

## 🔒 Security Best Practices

1. **Never store plain tokens** - Always encrypt
2. **Use UUID for IDs** - Prevents enumeration attacks
3. **Cascade deletes** - Clean up orphaned records
4. **Row-level security** - Users can only see their own data
5. **Audit logging** - Track who accessed what
6. **Regular backups** - Daily automated backups to S3

---

## 📊 Sample Data (Development)

```sql
-- Create test user
INSERT INTO users (google_id, email, name, default_preset)
VALUES ('google_123', 'test@example.com', 'Test User', 'portrait_pro');

-- Create subscription
INSERT INTO subscriptions (user_id, tier, monthly_limit)
SELECT id, 'creator', 100 FROM users WHERE email = 'test@example.com';

-- Create test job
INSERT INTO jobs (user_id, drive_file_id, drive_file_name, preset_name, status)
SELECT id, 'drive_abc123', 'test.jpg', 'portrait_pro', 'completed'
FROM users WHERE email = 'test@example.com';
```

---

*Schema will evolve based on product needs. All changes tracked via Alembic migrations.*
