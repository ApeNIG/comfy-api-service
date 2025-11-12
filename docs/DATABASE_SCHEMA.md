# Creator Platform Database Schema

## Overview

The Creator platform uses PostgreSQL with SQLAlchemy ORM and Alembic for migrations. The schema is designed for scalability, flexibility, and performance with proper indexing and relationship management.

## Core Principles

1. **UUID Primary Keys** - More secure than auto-increment, better for distributed systems
2. **JSONB for Flexibility** - Store dynamic data (tags, metadata, workflow JSON) without schema changes
3. **Timestamps** - Every table has `created_at` and `updated_at` for audit trails
4. **Soft Deletes** - Use `is_archived` flags instead of hard deletes where appropriate
5. **Denormalized Counters** - Store counts (workflow_count, generation_count) for performance
6. **Cascading Deletes** - User deletion cascades to all their data

## Tables

### `users`

Core user accounts with authentication, subscription, and usage tracking.

**Key Features:**
- Email-based authentication with password hashing
- Subscription tiers: FREE, CREATOR, STUDIO
- Monthly generation quotas (10/100/unlimited)
- API key management
- Stripe integration for billing

**Important Columns:**
- `monthly_generation_count` - Reset monthly, used for quota enforcement
- `api_key` - For API access, indexed for fast lookup
- `stripe_customer_id` - Links to Stripe customer
- `webhook_url` - Optional webhook for job completions

**Relationships:**
- One-to-many: `projects`, `workflows`, `generations`

**Business Logic:**
```python
# Check quota
user.has_quota_remaining  # Property method

# Increment usage
user.increment_usage()  # Auto-resets monthly

# Record login
user.record_login()  # Updates last_login_at and login_count
```

### `projects`

Organizational containers for workflows and generations.

**Use Cases:**
- "Marketing Campaign 2024"
- "Product Photoshoot - Winter Collection"
- "Brand Assets - Logo Variations"

**Key Features:**
- Folder organization
- Tags for filtering
- Custom metadata (JSON) for client info, deadlines, budget
- Public sharing with slugs
- Color coding for UI

**Important Columns:**
- `custom_metadata` - Flexible JSON for custom fields
- `public_slug` - For sharing: `/public/project/awesome-campaign-abc123`
- `workflow_count`, `generation_count` - Denormalized for performance
- `last_generation_at` - Show "active" projects

**Relationships:**
- Many-to-one: `user`
- One-to-many: `workflows`, `generations`

**Example Metadata:**
```json
{
  "client": "Acme Corp",
  "deadline": "2024-12-31",
  "budget": 5000,
  "campaign_type": "social_media",
  "deliverables": ["hero_image", "variants", "thumbnails"]
}
```

### `workflows`

ComfyUI workflow definitions with versioning and sharing.

**Key Features:**
- Stores complete ComfyUI JSON workflow
- Exposed parameters for UI form generation
- Version control (parent_version_id links to previous version)
- Template system (is_template flag)
- Usage tracking (use_count, copy_count)

**Important Columns:**
- `workflow_json` - The complete ComfyUI workflow in API format
- `parameters` - Exposed params for easy UI customization
- `features` - Feature flags: `{"use_adetailer": true, "use_upscaling": false}`
- `category` - For filtering: TEXT_TO_IMAGE, IMAGE_TO_IMAGE, etc.
- `visibility` - PRIVATE, PUBLIC, UNLISTED
- `estimated_credits` - Cost to run this workflow

**Workflow JSON Structure:**
```json
{
  "3": {
    "inputs": {
      "seed": 12345,
      "steps": 25,
      "cfg": 7.5,
      "sampler_name": "dpmpp_2m",
      "model": ["4", 0],
      "positive": ["6", 0]
    },
    "class_type": "KSampler"
  },
  "4": {
    "inputs": {"ckpt_name": "sd_v1_5.ckpt"},
    "class_type": "CheckpointLoaderSimple"
  }
}
```

**Parameters Structure:**
```json
{
  "prompt": {
    "type": "text",
    "label": "Prompt",
    "default": "beautiful landscape",
    "node_id": "6",
    "node_input": "text"
  },
  "steps": {
    "type": "number",
    "label": "Sampling Steps",
    "default": 25,
    "min": 10,
    "max": 50,
    "node_id": "3",
    "node_input": "steps"
  }
}
```

**Relationships:**
- Many-to-one: `user`, `project`
- One-to-many: `generations`, `versions`
- Self-referential: `parent_version_id` → `id`

**Version Control:**
```python
# Create new version
new_workflow = workflow.create_version(
    workflow_json=updated_json,
    notes="Added upscaling node"
)
```

### `generations`

Individual generation jobs and their results.

**Lifecycle:**
1. **QUEUED** - Job created, waiting to start
2. **PROCESSING** - ComfyUI is generating
3. **COMPLETED** - Success, images ready
4. **FAILED** - Error occurred
5. **CANCELLED** - User cancelled

**Key Features:**
- Complete input/output tracking
- Progress updates (0-100%)
- Error handling with retry logic
- User interaction (favorite, rating, notes)
- Webhook notifications
- Credits/cost tracking

**Important Columns:**
- `comfyui_prompt_id` - Links to ComfyUI job
- `input_parameters` - What user requested
- `workflow_snapshot` - Workflow JSON at generation time (for reproducibility)
- `output_urls` - Array of generated image URLs
- `duration_seconds` - Performance tracking
- `error_message`, `error_details` - For debugging
- `is_favorited` - User favorites (for gallery filtering)
- `credits_used` - For billing

**Timing Tracking:**
```python
# Start
generation.mark_processing()  # Sets started_at

# Complete
generation.mark_completed(
    output_urls=["url1", "url2"],
    duration=45.2
)  # Sets completed_at, calculates duration

# Failed
generation.mark_failed(
    error="Model not found",
    details={"model": "sd_xl.safetensors"}
)
```

**Progress Updates:**
```python
generation.update_progress(50, "Sampling step 15/30")
```

**Relationships:**
- Many-to-one: `user`, `project`, `workflow`

## Enums

### UserRole
- `USER` - Regular user
- `ADMIN` - Platform admin

### SubscriptionTier
- `FREE` - 10 generations/month
- `CREATOR` - 100 generations/month
- `STUDIO` - Unlimited

### SubscriptionStatus
- `ACTIVE` - Paying and active
- `CANCELLED` - Cancelled but still in billing period
- `PAST_DUE` - Payment failed
- `TRIALING` - In trial period
- `INCOMPLETE` - Setup not finished

### WorkflowCategory
- `TEXT_TO_IMAGE` - Generate from text
- `IMAGE_TO_IMAGE` - Transform existing image
- `INPAINTING` - Edit parts of image
- `UPSCALING` - Enhance resolution
- `CUSTOM` - User-defined workflow

### WorkflowVisibility
- `PRIVATE` - Only owner can see
- `PUBLIC` - Listed in marketplace
- `UNLISTED` - Public but not discoverable

### GenerationStatus
- `QUEUED` - Waiting to start
- `PROCESSING` - Currently generating
- `COMPLETED` - Success
- `FAILED` - Error
- `CANCELLED` - User cancelled

## Indexes

Critical indexes for performance:

**Users:**
- `email` - Login lookups
- `api_key` - API authentication

**Projects:**
- `user_id` - User's projects
- `public_slug` - Public sharing

**Workflows:**
- `user_id`, `project_id` - Filtering
- `category` - Browse by type
- `visibility` - Public workflows
- `is_template` - Official templates
- `public_slug` - Sharing

**Generations:**
- `user_id`, `project_id`, `workflow_id` - Filtering
- `status` - Job queue processing
- `comfyui_prompt_id` - Lookup by ComfyUI job
- `is_favorited` - User favorites

## Migrations

### Running Migrations

```bash
# Create new migration (after model changes)
alembic revision --autogenerate -m "Add feature X"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# View current version
alembic current

# View history
alembic history
```

### Initial Migration

The `001_create_creator_tables.py` migration creates all tables.

```bash
# Apply initial schema
alembic upgrade head
```

## Common Queries

### Get User's Recent Generations

```python
from apps.creator.models import Generation

generations = (
    db.query(Generation)
    .filter(Generation.user_id == user_id)
    .filter(Generation.status == GenerationStatus.COMPLETED)
    .order_by(Generation.created_at.desc())
    .limit(10)
    .all()
)
```

### Get Project with Counts

```python
from apps.creator.models import Project

project = db.query(Project).filter(Project.id == project_id).first()
print(f"Workflows: {project.workflow_count}")
print(f"Generations: {project.generation_count}")
```

### Find Public Workflows

```python
from apps.creator.models import Workflow, WorkflowVisibility

templates = (
    db.query(Workflow)
    .filter(Workflow.visibility == WorkflowVisibility.PUBLIC)
    .filter(Workflow.is_template == True)
    .order_by(Workflow.use_count.desc())
    .all()
)
```

### Check User Quota

```python
from apps.creator.models import User

user = db.query(User).filter(User.id == user_id).first()

if not user.has_quota_remaining:
    raise QuotaExceededError("Monthly limit reached")

# Increment after generation
user.increment_usage()
db.commit()
```

## Performance Considerations

1. **Denormalized Counters** - `workflow_count`, `generation_count` avoid expensive COUNT queries
2. **JSONB Indexing** - Can add GIN indexes on JSONB columns if needed:
   ```sql
   CREATE INDEX idx_workflows_features ON workflows USING GIN (features);
   ```
3. **Pagination** - Always use LIMIT/OFFSET or cursor-based pagination
4. **Eager Loading** - Use `joinedload()` to avoid N+1 queries:
   ```python
   projects = db.query(Project).options(
       joinedload(Project.workflows)
   ).all()
   ```

## Security

1. **No Sensitive Data in JSON** - Never store passwords, API keys in metadata/parameters
2. **Row-Level Security** - Always filter by `user_id` in queries
3. **Public Sharing** - Only expose via `public_slug`, never direct IDs
4. **API Keys** - Store hashed, use unique index
5. **Cascade Deletes** - User deletion removes all their data (GDPR compliance)

## Future Enhancements

- **Workflow Forking** - Copy and modify public workflows
- **Collaboration** - Share projects with team members
- **Collections** - Group workflows into collections
- **Comments** - Add comments to generations
- **Workflow Marketplace** - Buy/sell workflows
- **Analytics** - Track popular workflows, average durations
- **Audit Logs** - Track all changes for compliance

---

**Migration File:** [alembic/versions/001_create_creator_tables.py](../alembic/versions/001_create_creator_tables.py)

**Model Files:**
- [apps/creator/models/user.py](../apps/creator/models/user.py)
- [apps/creator/models/project.py](../apps/creator/models/project.py)
- [apps/creator/models/workflow.py](../apps/creator/models/workflow.py)
- [apps/creator/models/generation.py](../apps/creator/models/generation.py)
