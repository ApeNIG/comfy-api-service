# Creator Product - Architecture Overview

## 🎯 Product Vision

**Creator** is an indie-friendly SaaS product that automates image workflows using AI. Drop a file in Google Drive, get the processed result back automatically. Built on top of ComfyUI with a beautiful, delightful UX.

## 📁 Project Structure

```
apps/creator/               # Creator Product Backend (FastAPI)
├── main.py                 # FastAPI application entry point
├── dependencies.py         # Dependency injection (repositories, auth)
├── models/                 # SQLAlchemy models (Supabase schema)
│   ├── user.py            # User model with embedded subscription data
│   ├── project.py         # User projects (collections of workflows)
│   ├── workflow.py        # ComfyUI workflow templates
│   └── generation.py      # Job execution records
├── repositories/          # Data access layer (Repository pattern)
│   ├── base.py           # Base CRUD operations
│   └── user_repository.py # User-specific queries
├── services/             # Business logic layer
│   └── auth_service.py   # Authentication (bcrypt, JWT, password reset)
├── routers/              # API endpoints
│   └── auth.py           # Auth endpoints (/register, /login, /me, etc.)
├── utils/                # Utilities
│   ├── jwt.py            # JWT token creation/validation
│   └── password.py       # bcrypt password hashing
└── middleware/           # Request/response middleware
    ├── error_handler.py  # Friendly error messages
    └── rate_limiter.py   # Rate limiting

apps/web/                  # Web Frontend (HTML + HTMX)
├── routers/
│   └── pages.py          # HTML page routes
├── templates/            # Jinja2 templates
│   ├── auth.html         # Login/signup pages
│   ├── dashboard.html    # Main dashboard
│   └── onboarding.html   # Google Drive connection flow
└── static/               # CSS, JS, images
    ├── css/
    ├── js/
    └── images/

apps/shared/              # Shared infrastructure (used by both Creator and API)
├── infrastructure/
│   ├── database.py       # SQLAlchemy engine & session
│   ├── cache.py          # Redis connection
│   └── queue.py          # ARQ job queue
├── models/
│   ├── base.py           # SQLAlchemy Base
│   └── enums.py          # Shared enums (SubscriptionTier, UserRole, etc.)
└── services/
    ├── comfyui/          # ComfyUI client
    ├── storage/          # MinIO/S3 client
    └── email/            # Email service (SMTP)

config/                   # Configuration management
├── __init__.py           # Settings loader (dev/prod/test)
├── base.py               # Base settings (Pydantic)
├── development.py        # Dev-specific settings
└── production.py         # Prod-specific settings

alembic/                  # Database migrations
└── versions/             # Migration files
```

## 🏗️ Architecture Patterns

### 1. **Layered Architecture**

```
┌─────────────────────────────────────┐
│  Presentation Layer (Routers)      │  ← FastAPI endpoints
├─────────────────────────────────────┤
│  Business Logic (Services)         │  ← Authentication, Drive integration
├─────────────────────────────────────┤
│  Data Access (Repositories)        │  ← Database queries
├─────────────────────────────────────┤
│  Infrastructure (Database, Cache)  │  ← Supabase, Redis, MinIO
└─────────────────────────────────────┘
```

### 2. **Repository Pattern**
- Separates data access from business logic
- Example: `UserRepository` provides `find_by_email()`, `create()`, etc.
- Makes testing easier (can mock repositories)

### 3. **Service Layer**
- Encapsulates business logic
- Example: `AuthService` handles registration, login, password reset
- Coordinates between repositories and external services

### 4. **Dependency Injection**
- FastAPI's `Depends()` injects dependencies
- Example: `get_current_user()` injects authenticated user into routes
- Defined in `apps/creator/dependencies.py`

## 🗄️ Database Schema (Supabase PostgreSQL)

### **Users Table** (`users`)
```python
class User(Base):
    __tablename__ = "users"
    
    # Identity
    id: UUID (PK)
    email: str (unique, indexed)
    hashed_password: str
    full_name: str
    avatar_url: Optional[str]
    
    # OAuth
    google_id: Optional[str]
    google_refresh_token: Optional[str] (encrypted)
    
    # Status
    is_active: bool
    is_verified: bool
    role: str (USER, ADMIN)
    
    # Subscription (embedded - no separate table)
    subscription_tier: str (FREE, CREATOR, STUDIO)
    subscription_status: str (ACTIVE, CANCELED, PAST_DUE)
    trial_ends_at: datetime
    monthly_generation_count: int
    total_generations: int
    
    # Onboarding
    onboarding_completed: bool  ← NEW FIELD (just added!)
    
    # Security
    api_key: Optional[str]
    reset_token: Optional[str]
    reset_token_expires: Optional[datetime]
    
    # Tracking
    created_at: datetime
    last_login_at: Optional[datetime]
```

### **Projects Table** (`projects`)
User's project collections (e.g., "Product Photos", "Social Media Banners")

### **Workflows Table** (`workflows`)  
ComfyUI workflow templates with presets and parameters

### **Generations Table** (`generations`)
Job execution records (status, input/output URLs, ComfyUI prompt ID)

## 🔐 Authentication Flow

### Registration (`POST /auth/register`)
```
1. User submits email + password
2. AuthService validates email not taken
3. Password hashed with bcrypt (12 rounds)
4. User created with FREE tier + 7-day trial
5. Verification email sent (token stored in DB)
6. JWT token returned (7-day expiration)
7. Response includes trial status & jobs remaining
```

### Login (`POST /auth/login`)
```
1. User submits email + password
2. AuthService finds user by email
3. bcrypt verifies password (constant-time)
4. Login timestamp recorded
5. JWT token generated
6. Response includes onboarding_completed flag
   - If false → redirect to /onboarding
   - If true → redirect to /dashboard
```

### Password Reset
```
1. Request: POST /auth/forgot-password
   - Generates reset token (1-hour expiration)
   - Sends email with reset link
   
2. Reset: POST /auth/reset-password
   - Validates token & expiration
   - Hashes new password with bcrypt
   - Clears reset token
```

## 🔑 Key Technologies

### Backend
- **FastAPI** - Modern Python web framework (async, auto docs)
- **SQLAlchemy** - ORM for database interactions
- **Alembic** - Database migrations
- **Pydantic** - Data validation and settings management
- **bcrypt** - Password hashing (12 rounds)
- **PyJWT** - JWT token creation/validation
- **psycopg2** - PostgreSQL adapter

### Database & Storage
- **Supabase PostgreSQL** - Production database (EU West region)
- **Redis** - Caching & session storage
- **MinIO/S3** - File storage (generated images)

### Infrastructure
- **ComfyUI** - AI image generation backend (RunPod)
- **ARQ** - Async job queue (Redis-based)

### Frontend (Planned)
- **HTMX** - Dynamic HTML without heavy JS frameworks
- **Alpine.js** - Lightweight reactivity
- **TailwindCSS** - Utility-first CSS

## 🚀 Development Workflow

### Running Locally
```bash
# Set environment variables
export DATABASE_URL='postgresql://...'
export SECRET_KEY='...'

# Start Creator server
./run_creator.sh
# OR manually:
uvicorn apps.creator.main:app --host 0.0.0.0 --port 8001 --reload

# Access
# - API docs: http://localhost:8001/docs
# - Web UI: http://localhost:8001/login
```

### Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 📊 Current Status (Phase 2 Complete)

### ✅ Phase 1: Foundation
- FastAPI application structure
- Supabase database connection
- SQLAlchemy models
- Repository pattern

### ✅ Phase 2: Authentication
- Email/password registration
- bcrypt password hashing
- JWT token generation (7-day expiration)
- Password reset flow
- User model with subscription data embedded
- `onboarding_completed` field for flow control
- **Migration applied to Supabase** ✅

### 🚧 Phase 3: Google Drive Integration (TODO)
- OAuth 2.0 flow (Google)
- Drive folder watching
- File upload detection
- Automatic job triggering

### 🚧 Phase 4: Job Processing (TODO)
- ComfyUI workflow execution
- Progress tracking (WebSocket)
- Result storage (MinIO)
- Drive upload (processed images)

### 🚧 Phase 5: Billing & Subscriptions (TODO)
- Stripe integration
- Usage tracking & limits
- Subscription management

## 🔧 Recent Work

**Session Focus**: Authentication system upgrade + database migration

**Completed**:
1. ✅ Upgraded password hashing from SHA256 → bcrypt (12 rounds)
2. ✅ Implemented JWT utilities (7-day expiration, HS256)
3. ✅ Added password reset flow (1-hour token expiration)
4. ✅ Added `onboarding_completed` field to User model
5. ✅ Generated & applied Alembic migration to Supabase
6. ✅ Fixed import conflicts (archived old domain models)
7. ✅ Temporarily disabled SubscriptionRepository/JobRepository (use embedded data)

**Known Issues**:
- ⚠️ SSL connection issue when starting Creator server (environment-specific)
- Alembic migrations work fine, but FastAPI lifespan fails with SSL error
- Authentication code is ready but untested in full server environment

## 🎯 Next Steps

1. **Test Authentication** (Option 2 - partially complete)
   - Resolve SSL connection issue OR test in different environment
   - Verify registration creates users correctly
   - Test login flow & JWT validation
   - Test password reset flow

2. **Phase 3: Google Drive Integration** (2-3 hours)
   - OAuth 2.0 setup
   - Drive API integration
   - Folder watching logic
   - Onboarding flow UI

3. **Phase 4: Job Processing** (3-4 hours)
   - ComfyUI workflow execution
   - Job queue (ARQ)
   - Progress streaming (WebSocket)
   - Result delivery

## 📝 Notes

- **Architecture Decision**: Subscription data is embedded in User model (no separate Subscription table)
  - Simpler for indie product
  - Fewer joins
  - Good enough for 3 tiers (FREE, CREATOR, STUDIO)
  
- **Temporarily Disabled**: `SubscriptionRepository` and `JobRepository`
  - These were written for old domain-driven architecture
  - Need to be rewritten or removed once we finalize data model
  
- **Config System**: Uses Pydantic Settings with environment-based configs
  - `development.py` for local dev
  - `production.py` for deployed environments
  - `.env` file for secrets

