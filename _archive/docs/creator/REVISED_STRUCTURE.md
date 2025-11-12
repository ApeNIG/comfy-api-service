# Revised Production-Grade Structure

**Date:** 2025-11-10
**Status:** Recommended for Implementation

This document presents the **corrected, production-ready** directory structure that addresses all architectural concerns identified in the senior dev review.

---

## 🎯 Key Improvements Over Original

1. ✅ **Service Layer** - Business logic separated from routes
2. ✅ **Repository Pattern** - Data access isolated
3. ✅ **Dependency Injection** - Clean, testable dependencies
4. ✅ **Configuration Management** - Environment-specific configs
5. ✅ **Observability** - Structured logging, metrics, tracing
6. ✅ **Testing Infrastructure** - Unit, integration, e2e tests
7. ✅ **Middleware** - Auth, rate limiting, error handling
8. ✅ **Security** - Input validation, encryption, rate limiting

---

## 📁 Complete Directory Structure

```
comfy-api-service/
│
├── apps/
│   │
│   ├── api/                           # API Product (Developers)
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app initialization
│   │   ├── dependencies.py            # Dependency injection container
│   │   ├── config.py                  # API-specific settings
│   │   │
│   │   ├── middleware/                # Request/response middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # API key validation
│   │   │   ├── rate_limiter.py        # API rate limiting
│   │   │   ├── logging.py             # Request/response logging
│   │   │   └── error_handler.py       # Global error handling
│   │   │
│   │   ├── routers/                   # Route handlers (THIN)
│   │   │   ├── __init__.py
│   │   │   ├── generate.py            # POST /api/v1/generate/
│   │   │   ├── jobs.py                # POST /api/v1/jobs
│   │   │   └── health.py              # GET /health
│   │   │
│   │   ├── services/                  # Business logic (FAT)
│   │   │   ├── __init__.py
│   │   │   ├── generation_service.py  # Image generation logic
│   │   │   ├── job_service.py         # Job management
│   │   │   └── validation_service.py  # Input validation
│   │   │
│   │   └── models/                    # Pydantic models
│   │       ├── __init__.py
│   │       ├── requests.py            # Request DTOs
│   │       └── responses.py           # Response DTOs
│   │
│   ├── creator/                       # Creator Product (End Users)
│   │   ├── __init__.py
│   │   ├── main.py                    # Creator FastAPI app
│   │   ├── dependencies.py            # DI container
│   │   ├── config.py                  # Creator-specific settings
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── session_auth.py        # OAuth session validation
│   │   │   ├── rate_limiter.py        # Per-user rate limiting
│   │   │   ├── usage_tracker.py       # Monthly usage tracking
│   │   │   └── error_handler.py       # Error handling
│   │   │
│   │   ├── routers/                   # Route handlers (THIN)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # OAuth login/callback/logout
│   │   │   ├── dashboard.py           # Dashboard API
│   │   │   ├── drive.py               # Drive folder management
│   │   │   ├── presets.py             # Preset selection
│   │   │   ├── jobs.py                # Job history
│   │   │   └── billing.py             # Stripe integration
│   │   │
│   │   ├── services/                  # Business logic (FAT)
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py        # OAuth flow, token refresh
│   │   │   ├── drive_service.py       # Drive operations
│   │   │   ├── preset_service.py      # Preset management
│   │   │   ├── billing_service.py     # Stripe operations
│   │   │   ├── job_service.py         # Job management
│   │   │   ├── usage_service.py       # Usage tracking
│   │   │   └── notification_service.py # Email notifications
│   │   │
│   │   ├── repositories/              # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Base repository
│   │   │   ├── user_repository.py     # User CRUD
│   │   │   ├── subscription_repository.py
│   │   │   ├── job_repository.py
│   │   │   └── usage_repository.py
│   │   │
│   │   └── models/
│   │       ├── domain/                # Domain models (DB)
│   │       │   ├── __init__.py
│   │       │   ├── user.py            # SQLAlchemy User model
│   │       │   ├── subscription.py
│   │       │   ├── job.py
│   │       │   └── usage.py
│   │       │
│   │       └── dto/                   # Data transfer objects
│   │           ├── __init__.py
│   │           ├── requests.py        # Pydantic request models
│   │           └── responses.py       # Pydantic response models
│   │
│   ├── shared/                        # Shared Infrastructure
│   │   ├── __init__.py
│   │   │
│   │   ├── infrastructure/            # Core infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── database.py            # SQLAlchemy session mgmt
│   │   │   ├── cache.py               # Redis client
│   │   │   ├── queue.py               # Dramatiq broker setup
│   │   │   └── storage.py             # Storage factory
│   │   │
│   │   ├── services/                  # Shared business services
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── comfyui/               # ComfyUI integration
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py          # ComfyUI HTTP client
│   │   │   │   ├── workflow_runner.py # Run workflows
│   │   │   │   └── preset_loader.py   # Load preset JSONs
│   │   │   │
│   │   │   ├── storage/               # Storage abstraction
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py            # StorageProvider interface
│   │   │   │   ├── drive.py           # GoogleDriveProvider
│   │   │   │   ├── minio.py           # MinIOProvider
│   │   │   │   └── s3.py              # S3Provider (future)
│   │   │   │
│   │   │   ├── email/                 # Email service
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py            # EmailProvider interface
│   │   │   │   ├── smtp.py            # SMTP provider
│   │   │   │   └── sendgrid.py        # SendGrid (future)
│   │   │   │
│   │   │   └── encryption/            # Security services
│   │   │       ├── __init__.py
│   │   │       ├── token_encryptor.py # Encrypt OAuth tokens
│   │   │       └── password_hasher.py # Hash passwords
│   │   │
│   │   ├── models/                    # Shared domain models
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Base SQLAlchemy model
│   │   │   └── enums.py               # Shared enums
│   │   │
│   │   └── utils/                     # Utilities
│   │       ├── __init__.py
│   │       ├── logger.py              # Structured logging setup
│   │       ├── retry.py               # Retry decorator
│   │       ├── validators.py          # Custom validators
│   │       └── metrics.py             # Prometheus metrics
│   │
│   ├── worker/                        # Background Workers
│   │   ├── __init__.py
│   │   ├── broker.py                  # Dramatiq broker config
│   │   ├── config.py                  # Worker settings
│   │   │
│   │   ├── tasks/                     # Task definitions (thin)
│   │   │   ├── __init__.py
│   │   │   ├── api_tasks.py           # API-triggered tasks
│   │   │   ├── creator_tasks.py       # Creator-triggered tasks
│   │   │   └── maintenance_tasks.py   # Cron tasks
│   │   │
│   │   ├── handlers/                  # Task logic (fat)
│   │   │   ├── __init__.py
│   │   │   ├── image_processor.py     # ComfyUI processing
│   │   │   ├── drive_uploader.py      # Upload to Drive
│   │   │   └── notification_sender.py # Send emails
│   │   │
│   │   └── presets/                   # Preset workflow files
│   │       ├── portrait_pro.json
│   │       ├── product_glow.json
│   │       └── cinematic.json
│   │
│   └── web/                           # Frontend (Creator Dashboard)
│       ├── static/
│       │   ├── css/
│       │   │   ├── main.css           # Global styles
│       │   │   └── components.css     # Component styles
│       │   │
│       │   ├── js/
│       │   │   ├── main.js            # App initialization
│       │   │   ├── auth.js            # OAuth flow
│       │   │   ├── dashboard.js       # Dashboard logic
│       │   │   └── api.js             # API client
│       │   │
│       │   └── images/
│       │       ├── logo.svg
│       │       └── presets/           # Preset preview images
│       │
│       └── templates/
│           ├── base.html              # Base template
│           ├── dashboard.html         # Main dashboard
│           ├── settings.html          # User settings
│           └── billing.html           # Billing page
│
├── tests/                             # Test Suite
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   │
│   ├── unit/                          # Unit tests
│   │   ├── __init__.py
│   │   ├── services/                  # Test services
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_drive_service.py
│   │   │   └── test_billing_service.py
│   │   │
│   │   ├── repositories/              # Test repositories
│   │   │   ├── test_user_repository.py
│   │   │   └── test_job_repository.py
│   │   │
│   │   └── utils/                     # Test utilities
│   │       └── test_validators.py
│   │
│   ├── integration/                   # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api_endpoints.py      # API routes
│   │   ├── test_creator_endpoints.py  # Creator routes
│   │   ├── test_drive_integration.py  # Drive API
│   │   ├── test_stripe_integration.py # Stripe API
│   │   └── test_database.py           # DB operations
│   │
│   ├── e2e/                           # End-to-end tests
│   │   ├── __init__.py
│   │   └── test_full_workflow.py      # Complete user flows
│   │
│   └── fixtures/                      # Test data
│       ├── images/                    # Sample images
│       │   ├── portrait.jpg
│       │   └── product.jpg
│       │
│       ├── workflows/                 # Sample workflows
│       │   └── test_preset.json
│       │
│       └── data.py                    # Test data factories
│
├── alembic/                           # Database Migrations
│   ├── versions/                      # Migration files
│   │   └── 001_initial_schema.py
│   │
│   ├── env.py                         # Alembic config
│   └── script.py.mako                 # Migration template
│
├── config/                            # Configuration Management
│   ├── __init__.py                    # Config factory
│   ├── base.py                        # Base settings
│   ├── development.py                 # Dev overrides
│   ├── production.py                  # Prod overrides
│   └── testing.py                     # Test overrides
│
├── scripts/                           # Utility Scripts
│   ├── seed_database.py               # Seed test data
│   ├── migrate_users.py               # Data migrations
│   ├── generate_api_keys.py           # Create API keys
│   └── cleanup_jobs.py                # Archive old jobs
│
├── deploy/                            # Deployment configs
│   ├── docker/
│   │   ├── Dockerfile.api             # API container
│   │   ├── Dockerfile.worker          # Worker container
│   │   └── Dockerfile.web             # Static web
│   │
│   ├── kubernetes/                    # K8s manifests (future)
│   │   ├── api-deployment.yaml
│   │   └── worker-deployment.yaml
│   │
│   └── nginx/
│       └── nginx.conf                 # Reverse proxy config
│
├── _archive/                          # Documentation
│   ├── README.md
│   └── docs/
│       ├── api/
│       ├── creator/
│       └── shared/
│
├── .github/                           # GitHub Actions
│   └── workflows/
│       ├── ci.yml                     # CI pipeline
│       └── deploy.yml                 # CD pipeline
│
├── .env.example                       # Environment template
├── .env                               # Local env (gitignored)
├── .gitignore
│
├── docker-compose.yml                 # Local development
├── docker-compose.prod.yml            # Production
│
├── Dockerfile                         # Multi-stage build
├── pyproject.toml                     # Dependencies
├── poetry.lock                        # Locked dependencies
├── pytest.ini                         # Pytest config
│
└── README.md                          # Project overview
```

---

## 🔧 Key Files Explained

### **Dependency Injection Container**

`apps/creator/dependencies.py`:
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from apps.shared.infrastructure.database import get_db
from apps.creator.services.auth_service import AuthService
from apps.creator.repositories.user_repository import UserRepository
from apps.shared.services.encryption.token_encryptor import TokenEncryptor

# Repository Dependencies
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

# Service Dependencies
def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    encryptor: TokenEncryptor = Depends()
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        encryptor=encryptor,
        google_client_id=settings.GOOGLE_CLIENT_ID,
        google_client_secret=settings.GOOGLE_CLIENT_SECRET
    )

# Auth Middleware
async def get_current_user(
    session: str = Cookie(None),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    if not session:
        raise HTTPException(401, "Not authenticated")

    payload = jwt.decode(session, settings.SECRET_KEY)
    user = await user_repo.find_by_id(payload["user_id"])

    if not user:
        raise HTTPException(401, "User not found")

    return user
```

---

### **Base Repository**

`apps/creator/repositories/base.py`:
```python
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations"""

    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    async def find_by_id(self, id: UUID) -> Optional[T]:
        return self.db.query(self.model).filter_by(id=id).first()

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        return (
            self.db.query(self.model)
            .limit(limit)
            .offset(offset)
            .all()
        )

    async def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs) -> T:
        instance = await self.find_by_id(id)
        if not instance:
            raise ValueError(f"{self.model.__name__} not found")

        for key, value in kwargs.items():
            setattr(instance, key, value)

        self.db.commit()
        self.db.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        instance = await self.find_by_id(id)
        if not instance:
            return False

        self.db.delete(instance)
        self.db.commit()
        return True
```

---

### **Service Example**

`apps/creator/services/drive_service.py`:
```python
from uuid import UUID
from typing import List
import structlog
from apps.creator.repositories.user_repository import UserRepository
from apps.shared.services.storage.drive import GoogleDriveProvider
from apps.shared.services.encryption.token_encryptor import TokenEncryptor

logger = structlog.get_logger(__name__)

class DriveService:
    """Business logic for Google Drive operations"""

    def __init__(
        self,
        user_repo: UserRepository,
        drive_provider: GoogleDriveProvider,
        encryptor: TokenEncryptor
    ):
        self.user_repo = user_repo
        self.drive_provider = drive_provider
        self.encryptor = encryptor

    async def connect_user_drive(self, user_id: UUID, auth_code: str):
        """Connect user's Google Drive account"""
        logger.info("connecting_user_drive", user_id=str(user_id))

        # Exchange code for tokens
        tokens = await self.drive_provider.exchange_code(auth_code)

        # Encrypt tokens
        encrypted_access = self.encryptor.encrypt(tokens.access_token)
        encrypted_refresh = self.encryptor.encrypt(tokens.refresh_token)

        # Save to database
        await self.user_repo.update(
            id=user_id,
            drive_access_token=encrypted_access,
            drive_refresh_token=encrypted_refresh,
            drive_token_expires_at=tokens.expires_at
        )

        logger.info("user_drive_connected", user_id=str(user_id))

    async def list_folders(self, user_id: UUID) -> List[dict]:
        """List user's Drive folders"""
        user = await self.user_repo.find_by_id(user_id)

        # Decrypt token
        access_token = self.encryptor.decrypt(user.drive_access_token)

        # List folders
        return await self.drive_provider.list_folders(access_token)

    async def set_watched_folder(
        self,
        user_id: UUID,
        folder_id: str
    ):
        """Set which folder to watch for uploads"""
        # Create output folder
        user = await self.user_repo.find_by_id(user_id)
        access_token = self.encryptor.decrypt(user.drive_access_token)

        output_folder_id = await self.drive_provider.create_folder(
            access_token,
            name="Edited Photos",
            parent_id=folder_id
        )

        # Save to database
        await self.user_repo.update(
            id=user_id,
            watched_folder_id=folder_id,
            output_folder_id=output_folder_id
        )

        logger.info(
            "watched_folder_set",
            user_id=str(user_id),
            folder_id=folder_id
        )
```

---

### **Route Handler Example**

`apps/creator/routers/drive.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from apps.creator.dependencies import get_drive_service, get_current_user
from apps.creator.services.drive_service import DriveService
from apps.creator.models.domain.user import User
from apps.creator.models.dto.responses import FolderListResponse

router = APIRouter(prefix="/drive", tags=["Drive"])

@router.post("/connect")
async def connect_drive(
    code: str,
    drive_service: DriveService = Depends(get_drive_service),
    current_user: User = Depends(get_current_user)
):
    """
    Connect user's Google Drive account

    Route handler is THIN - just validates input and delegates
    """
    await drive_service.connect_user_drive(current_user.id, code)
    return {"status": "connected"}

@router.get("/folders", response_model=FolderListResponse)
async def list_folders(
    drive_service: DriveService = Depends(get_drive_service),
    current_user: User = Depends(get_current_user)
):
    """List user's Drive folders"""
    folders = await drive_service.list_folders(current_user.id)
    return FolderListResponse(folders=folders)

@router.post("/watch")
async def set_watched_folder(
    folder_id: str,
    drive_service: DriveService = Depends(get_drive_service),
    current_user: User = Depends(get_current_user)
):
    """Set folder to watch for new uploads"""
    await drive_service.set_watched_folder(current_user.id, folder_id)
    return {"status": "watching", "folder_id": folder_id}
```

---

## 📊 Benefits of This Structure

### **1. Testability**
```python
# Easy to test services in isolation
def test_drive_service_connect():
    # Mock dependencies
    mock_user_repo = MagicMock()
    mock_drive_provider = MagicMock()
    mock_encryptor = MagicMock()

    # Create service
    service = DriveService(mock_user_repo, mock_drive_provider, mock_encryptor)

    # Test business logic
    await service.connect_user_drive(user_id, "test_code")

    # Assert
    mock_drive_provider.exchange_code.assert_called_once()
```

### **2. Reusability**
```python
# Same service used in API and worker
# apps/creator/routers/drive.py
async def connect_drive(drive_service: DriveService = Depends()):
    await drive_service.connect_user_drive(...)

# apps/worker/tasks/creator_tasks.py
@actor
async def refresh_drive_tokens():
    drive_service = DriveService(...)
    await drive_service.refresh_tokens(...)
```

### **3. Maintainability**
- Clear separation of concerns
- Easy to find code (predictable structure)
- Changes isolated (modify service, not route)

### **4. Scalability**
- Horizontal scaling (stateless services)
- Easy to add caching
- Can split into microservices later

---

## ✅ Implementation Priority

### **Phase 0: Foundation (Before Coding)**
1. Create directory structure
2. Set up configuration management (`config/`)
3. Add logging infrastructure (`apps/shared/utils/logger.py`)
4. Create base classes (Repository, Service)
5. Set up dependency injection (`dependencies.py`)

### **Phase 1: Core Infrastructure**
1. Database setup (`apps/shared/infrastructure/database.py`)
2. Redis setup (`apps/shared/infrastructure/cache.py`)
3. Storage abstraction (`apps/shared/services/storage/`)
4. Test fixtures (`tests/conftest.py`)

### **Phase 2: Creator Features**
1. Auth service + routes
2. Drive service + routes
3. Job service + routes
4. Billing service + routes

---

**This structure is production-ready, maintainable, and scalable. Recommend implementing BEFORE Phase 2 coding begins.**

---

*Questions? Review apps/shared/infrastructure/* for infrastructure examples.
