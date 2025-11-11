# Creator - Image Automation for Indie Creators

Beautiful, delightful image automation powered by AI.

## Overview

Creator is a SaaS product built on top of ComfyUI that enables indie creators to automate image workflows through Google Drive integration.

### Key Features

✨ **One-Click Setup**
- Google OAuth authentication (no passwords!)
- Automatic folder creation
- Smart defaults everywhere

🎨 **Beautiful UX**
- Glassmorphism design with animations
- Real-time progress updates
- Friendly error messages
- Celebration effects

📊 **Transparent Pricing**
- **Free**: 10 jobs/month (7-day trial)
- **Creator**: 100 jobs/month ($9/mo)
- **Studio**: 500 jobs/month ($29/mo)

💪 **Powerful**
- ComfyUI workflows
- Batch processing
- WebSocket progress streaming
- Google Drive integration

## Getting Started

### Prerequisites

1. **Python 3.11+**
2. **PostgreSQL** (or SQLite for development)
3. **Redis** (for caching and rate limiting)
4. **ComfyUI** running locally or remotely
5. **Google OAuth credentials** (for Drive integration)
6. **Stripe account** (for payments)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/comfy-api-service.git
   cd comfy-api-service
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Set up Google OAuth**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable Google Drive API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URI: `http://localhost:8001/auth/google/callback`
   - Copy Client ID and Client Secret to `.env`

5. **Set up Stripe** (optional, for payments):
   - Go to [Stripe Dashboard](https://dashboard.stripe.com)
   - Get your API keys
   - Copy to `.env`

6. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

7. **Start the server**:
   ```bash
   ./run_creator.sh
   ```

8. **Open your browser**:
   - Web UI: http://localhost:8001
   - API Docs: http://localhost:8001/docs

## Architecture

```
Creator
├── Services Layer (Business Logic)
│   ├── AuthService - Authentication with Google OAuth
│   ├── DriveService - Google Drive integration
│   ├── JobService - Image processing workflows
│   └── SubscriptionService - Billing and usage tracking
│
├── Routers (API Endpoints)
│   ├── /auth - Login, signup, OAuth
│   ├── /drive - Connect Drive, watch folders
│   ├── /jobs - Submit jobs, get status
│   └── /subscriptions - Billing and upgrades
│
├── Repositories (Data Access)
│   ├── UserRepository
│   ├── SubscriptionRepository
│   └── JobRepository
│
└── Models (Domain Objects)
    ├── User
    ├── Subscription
    └── Job
```

## Environment Variables

### Required

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/creator

# Security
SECRET_KEY=your-secret-key-for-jwt-signing
ENCRYPTION_KEY=your-encryption-key-for-tokens

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8001/auth/google/callback

# Stripe
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# ComfyUI
COMFYUI_URL=http://localhost:8188
```

### Optional

```bash
# Environment
ENVIRONMENT=development
DEBUG=true
FRONTEND_URL=http://localhost:8001

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature flags
FEATURE_DRIVE_INTEGRATION=true
FEATURE_STRIPE_BILLING=true
FEATURE_EMAIL_NOTIFICATIONS=true
```

## Usage

### 1. Sign Up

Visit http://localhost:8001/signup and create an account:
- Enter your email, name, and password
- Or sign up with Google (recommended)

You'll automatically get:
- 7-day free trial
- 10 free jobs
- Welcome email (if SMTP configured)

### 2. Connect Google Drive

After signing up, you'll be guided through:
1. Authorize Creator to access your Drive
2. Choose or create a folder to watch
3. Test the integration with a sample upload

### 3. Upload Images

Simply drop images into your watched folder:
- Creator detects the upload automatically
- Processes the image using ComfyUI
- Saves the result back to your Drive
- Sends you an email when done

### 4. Monitor Progress

Visit the dashboard to see:
- Active jobs with real-time progress
- Completed jobs with thumbnails
- Usage stats (jobs remaining, trial days)
- Subscription details

## API Examples

### Register with Email

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "creator@example.com",
    "password": "securepassword123",
    "full_name": "John Creator"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Welcome to Creator, John Creator! 🎉 Check your email.",
  "user": {
    "id": "uuid",
    "email": "creator@example.com",
    "full_name": "John Creator",
    "is_verified": false
  },
  "subscription": {
    "tier": "free",
    "trial_days_remaining": 7,
    "jobs_remaining": 10
  },
  "next_step": "/onboarding/connect-drive",
  "onboarding_complete": false
}
```

### Login with Email

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "creator@example.com",
    "password": "securepassword123"
  }'
```

### Connect Google Drive

```bash
# Step 1: Get OAuth URL
curl http://localhost:8001/auth/google

# Step 2: User authorizes in browser

# Step 3: Callback handles token exchange automatically
```

### Submit Job

```bash
curl -X POST http://localhost:8001/jobs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "thumbnail_generator",
    "input_files": ["drive://file-id-123"],
    "parameters": {
      "width": 1920,
      "height": 1080
    }
  }'
```

## Development

### Project Structure

```
apps/creator/
├── main.py              # FastAPI app initialization
├── routers/             # API endpoints
│   ├── auth.py         # Authentication routes
│   ├── drive.py        # Google Drive routes
│   ├── jobs.py         # Job management routes
│   └── subscriptions.py # Billing routes
├── services/            # Business logic
│   ├── auth_service.py
│   ├── drive_service.py
│   ├── job_service.py
│   └── subscription_service.py
├── repositories/        # Data access
│   ├── user_repository.py
│   ├── subscription_repository.py
│   └── job_repository.py
└── models/             # Domain models
    └── domain.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps/creator --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Code Style

We use:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **flake8** for linting

```bash
# Format code
black apps/creator

# Sort imports
isort apps/creator

# Type check
mypy apps/creator

# Lint
flake8 apps/creator
```

## Deployment

### Docker

```bash
# Build image
docker build -t creator:latest .

# Run container
docker run -p 8001:8001 \
  -e DATABASE_URL=postgresql://... \
  -e GOOGLE_CLIENT_ID=... \
  creator:latest
```

### Docker Compose

```bash
# Start all services (app + postgres + redis)
docker-compose up -d

# View logs
docker-compose logs -f creator

# Stop services
docker-compose down
```

### Production Checklist

- [ ] Set strong `SECRET_KEY` and `ENCRYPTION_KEY`
- [ ] Use production database (PostgreSQL)
- [ ] Configure Redis for caching
- [ ] Set up SMTP for emails
- [ ] Configure Sentry for error tracking
- [ ] Enable HTTPS/SSL
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Configure rate limiting
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure backups
- [ ] Set up CI/CD pipeline

## Troubleshooting

### "Google OAuth error"

Make sure:
1. You've enabled Google Drive API in Cloud Console
2. Redirect URI matches exactly: `http://localhost:8001/auth/google/callback`
3. OAuth consent screen is configured
4. Client ID and secret are correct in `.env`

### "Database connection failed"

Check:
1. PostgreSQL is running: `pg_isready`
2. Database exists: `createdb creator`
3. DATABASE_URL is correct in `.env`
4. Migrations are applied: `alembic upgrade head`

### "ComfyUI not responding"

Verify:
1. ComfyUI is running: `curl http://localhost:8188/system_stats`
2. COMFYUI_URL is correct in `.env`
3. Network connectivity

### "Redis connection failed"

Check:
1. Redis is running: `redis-cli ping`
2. REDIS_URL is correct in `.env`

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

MIT License. See [LICENSE](../../LICENSE) for details.

## Support

- **Documentation**: https://docs.creator.com
- **Email**: support@creator.com
- **GitHub Issues**: https://github.com/yourusername/creator/issues
- **Discord**: https://discord.gg/creator

## Roadmap

### Phase 1: Foundation ✅
- [x] Auth with Google OAuth
- [x] Beautiful login/signup UI
- [x] Database models and migrations
- [x] Core services (encryption, email, ComfyUI)

### Phase 2: Drive Integration (Current)
- [ ] Connect Google Drive
- [ ] Watch folders for uploads
- [ ] Handle webhooks
- [ ] Upload results back to Drive

### Phase 3: Job Processing
- [ ] Submit jobs from Drive uploads
- [ ] Real-time progress updates
- [ ] Download results
- [ ] Email notifications

### Phase 4: Billing
- [ ] Stripe integration
- [ ] Subscription management
- [ ] Usage tracking
- [ ] Upgrade/downgrade flows

### Phase 5: Polish
- [ ] Dashboard with charts
- [ ] Settings page
- [ ] Workflow customization
- [ ] Batch processing
- [ ] API rate limiting

### Phase 6: Scale
- [ ] Multi-tenancy
- [ ] Team collaboration
- [ ] Advanced workflows
- [ ] Analytics
- [ ] Mobile app

---

Built with ❤️ by creators, for creators.
