# Supabase Setup for Creator Platform

## Why Supabase?

Supabase provides a complete backend solution:
- **PostgreSQL Database** - Same models we built work perfectly
- **Authentication** - Built-in auth system (can use alongside our custom auth)
- **Storage** - S3-compatible storage for generated images
- **Real-time** - WebSocket subscriptions for live progress updates
- **Edge Functions** - Serverless functions for webhooks
- **Auto-scaling** - Handles growth automatically
- **Free Tier** - Perfect for MVP

## Setup Steps

### 1. Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign in with GitHub
3. Click "New Project"
4. Choose organization (create one if needed)
5. Fill in project details:
   - **Name:** `creator-platform`
   - **Database Password:** Generate a strong password (save it!)
   - **Region:** Choose closest to your users
   - **Pricing Plan:** Free (for now)
6. Click "Create new project"
7. Wait 1-2 minutes for provisioning

### 2. Get Connection Details

Once project is ready:

1. Go to **Settings** → **Database**
2. Find **Connection string** section
3. Copy the **URI** (Connection pooling mode)
4. It looks like: `postgresql://postgres.[project-ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres`

### 3. Update .env

```bash
# Replace DATABASE_URL in .env
DATABASE_URL=postgresql://postgres.[your-project-ref]:[your-password]@[your-host]:6543/postgres

# Add Supabase keys (from Settings → API)
SUPABASE_URL=https://[your-project-ref].supabase.co
SUPABASE_ANON_KEY=eyJhbG...  # Public anon key
SUPABASE_SERVICE_KEY=eyJhbG...  # Secret service role key (keep secure!)
```

**Important:** Use the **pooler connection** (port 6543), not direct connection (port 5432). Pooler handles concurrent connections better.

### 4. Run Migrations

```bash
# Install Supabase CLI (optional but helpful)
npm install -g supabase

# Or use Alembic directly
alembic upgrade head
```

This creates all tables in your Supabase database.

### 5. Verify in Supabase Dashboard

1. Go to **Table Editor** in Supabase dashboard
2. You should see:
   - `users`
   - `projects`
   - `workflows`
   - `generations`

## Supabase Features We Can Use

### 1. Storage for Generated Images

Instead of local filesystem, use Supabase Storage:

```python
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Upload generated image
with open("image.png", "rb") as f:
    res = supabase.storage.from_("generations").upload(
        path=f"user_{user_id}/{generation_id}.png",
        file=f,
        file_options={"content-type": "image/png"}
    )

# Get public URL
url = supabase.storage.from_("generations").get_public_url(
    f"user_{user_id}/{generation_id}.png"
)
```

**Setup:**
1. Go to **Storage** in Supabase dashboard
2. Create bucket: `generations`
3. Set to **Public** (or Private if you want auth)
4. Configure CORS if needed

### 2. Real-time Progress Updates

Use Supabase real-time for WebSocket updates:

```python
# Backend: Update generation progress (triggers real-time)
generation.progress_percent = 50
generation.progress_message = "Sampling..."
db.commit()

# Frontend: Subscribe to changes
const channel = supabase
  .channel('generation-progress')
  .on(
    'postgres_changes',
    {
      event: 'UPDATE',
      schema: 'public',
      table: 'generations',
      filter: `id=eq.${generationId}`
    },
    (payload) => {
      console.log('Progress:', payload.new.progress_percent)
    }
  )
  .subscribe()
```

**Setup:**
1. Go to **Database** → **Replication**
2. Enable replication for `generations` table

### 3. Row Level Security (RLS)

Supabase has built-in row-level security:

```sql
-- Users can only see their own data
CREATE POLICY "Users can view own projects"
ON projects
FOR SELECT
USING (auth.uid() = user_id);

-- Users can only create projects for themselves
CREATE POLICY "Users can create own projects"
ON projects
FOR INSERT
WITH CHECK (auth.uid() = user_id);
```

**Setup:**
1. Go to **Authentication** → **Policies**
2. Enable RLS on tables
3. Add policies (can be added in migrations)

### 4. Edge Functions for Webhooks

Deploy webhook handlers to Supabase:

```typescript
// supabase/functions/generation-complete/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

serve(async (req) => {
  const { generation_id } = await req.json()

  // Send webhook to user's URL
  // Send email notification
  // Update analytics

  return new Response(JSON.stringify({ success: true }))
})
```

## Configuration Options

### Development vs Production

```bash
# Development (.env.local)
DATABASE_URL=postgresql://postgres.dev-ref:[password]@[host]:6543/postgres
SUPABASE_URL=https://dev-ref.supabase.co

# Production (.env.production)
DATABASE_URL=postgresql://postgres.prod-ref:[password]@[host]:6543/postgres
SUPABASE_URL=https://prod-ref.supabase.co
```

### Connection Pooling

Supabase provides two connection modes:

**1. Direct Connection** (port 5432)
- Use for migrations
- Limited connections (max 60)
- `postgresql://postgres.[ref]:[pass]@[host]:5432/postgres`

**2. Pooler Connection** (port 6543) **← Use This**
- Use for application
- Handles thousands of connections
- `postgresql://postgres.[ref]:[pass]@[host]:6543/postgres`

### Best Practices

1. **Use Pooler in App** - Set DATABASE_URL to pooler (port 6543)
2. **Use Direct for Migrations** - Alembic works better with direct connection
3. **Environment Variables** - Never commit credentials
4. **Service Role Key** - Keep SUPABASE_SERVICE_KEY secure (server-side only)
5. **Anon Key** - SUPABASE_ANON_KEY can be public (frontend)

## Migration Strategy

### Option 1: Fresh Supabase Database

If starting fresh:
```bash
# Just run migrations
alembic upgrade head
```

### Option 2: Migrating from Local

If you have local data to migrate:

```bash
# 1. Dump local database
pg_dump postgresql://comfyui:comfyui_dev@localhost:5432/comfyui_creator > backup.sql

# 2. Clean and restore to Supabase
psql postgresql://postgres.[ref]:[pass]@[host]:5432/postgres < backup.sql

# 3. Update .env to use Supabase
# 4. Test application
```

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql postgresql://postgres.[ref]:[pass]@[host]:6543/postgres

# If fails, check:
# 1. Password is correct
# 2. Using pooler port (6543)
# 3. Project is not paused
```

### Migration Errors

```bash
# If migration fails, check current state
alembic current

# Stamp database to specific version
alembic stamp head

# Retry migration
alembic upgrade head
```

### RLS Blocking Queries

If queries fail after enabling RLS:

```sql
-- Temporarily disable RLS for testing
ALTER TABLE projects DISABLE ROW LEVEL SECURITY;

-- Re-enable and add proper policies
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
```

## Cost Estimation

**Free Tier Limits:**
- 500MB database
- 1GB storage
- 2GB bandwidth
- 50,000 monthly active users

**When to Upgrade:**
- Database > 500MB → Pro ($25/month for 8GB)
- Need more bandwidth → Pro
- Want point-in-time recovery → Pro
- Need dedicated resources → Pro

For MVP, **Free tier is plenty**.

## Next Steps

1. ✅ Create Supabase project
2. ✅ Update .env with connection string
3. ✅ Run migrations: `alembic upgrade head`
4. ✅ Verify tables in Supabase dashboard
5. Configure storage bucket for images
6. Set up RLS policies
7. Deploy Edge Functions (optional)

## Resources

- [Supabase Docs](https://supabase.com/docs)
- [Python Client](https://github.com/supabase-community/supabase-py)
- [Storage Guide](https://supabase.com/docs/guides/storage)
- [Real-time Guide](https://supabase.com/docs/guides/realtime)

---

**Ready to switch?** Update your `.env` and run `alembic upgrade head`!
