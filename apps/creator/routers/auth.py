"""
Authentication routes with delightful UX

API Design Philosophy:
- Every response tells a story
- Error messages guide users to success
- Success messages celebrate wins
- Consistent, predictable structure

Examples of GOOD vs BAD responses:

BAD:  {"error": "Invalid credentials"}
GOOD: {
    "error": "auth_failed",
    "message": "That password doesn't match. Try again, or use 'Forgot Password' to reset it.",
    "action": "retry",
    "help_url": "/help/login-issues"
}

BAD:  {"success": true}
GOOD: {
    "success": true,
    "message": "Welcome back, Jane! 👋",
    "user": {...},
    "next_step": "/dashboard"
}
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta
import jwt

from apps.creator.services.auth_service import AuthService, AuthError, get_auth_service
from apps.creator.repositories import UserRepository, SubscriptionRepository
from apps.creator.dependencies import get_user_repository, get_subscription_repository, get_current_user
from apps.creator.models.domain import User
from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

router = APIRouter(tags=["🔐 Authentication"])


# ==================== JWT Token Generation ====================

def create_access_token(user_id: str, email: str, expires_delta: timedelta = None) -> str:
    """
    Generate JWT access token for user session.

    Token contains:
    - user_id: For user identification
    - email: For convenience
    - exp: Expiration timestamp
    - iat: Issued at timestamp

    Args:
        user_id: User's UUID
        email: User's email
        expires_delta: Token lifetime (default: 7 days)

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(days=7)  # Default 7-day session

    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": user_id,  # Standard JWT claim for subject (user ID)
        "email": email,
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


# ==================== Request/Response Models ====================

class RegisterRequest(BaseModel):
    """User registration with email/password."""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: Optional[str] = Field(None, description="Your name (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "jane@example.com",
                "password": "secure_password_123",
                "full_name": "Jane Doe"
            }
        }


class LoginRequest(BaseModel):
    """User login with email/password."""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "jane@example.com",
                "password": "secure_password_123"
            }
        }


class AuthResponse(BaseModel):
    """Successful authentication response."""
    success: bool = True
    message: str = Field(..., description="Friendly success message")
    access_token: str = Field(..., description="JWT access token for API requests")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    user: dict = Field(..., description="User profile")
    subscription: dict = Field(..., description="Subscription info")
    next_step: str = Field(..., description="Where to go next")
    onboarding_complete: bool = Field(..., description="Has user completed onboarding?")


# ==================== Routes ====================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up with email",
    description="Create a new account. You'll get a 7-day free trial to try everything!",
)
async def register(
    data: RegisterRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Register new user with email/password.

    UX Flow:
    1. User submits email + password
    2. We create account + free trial
    3. Send verification email
    4. Return success with next steps

    Returns:
        🎉 Success response with user profile and next step
    """
    try:
        auth_service = get_auth_service(user_repo, subscription_repo)

        user, verification_token = await auth_service.register_with_email(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )

        # Get subscription
        subscription = subscription_repo.find_by_user_id(user.id)

        # Generate JWT access token
        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email
        )

        # Build response with helpful guidance
        return AuthResponse(
            success=True,
            message=f"Welcome to Creator, {user.full_name}! 🎉 Check your email to verify your account.",
            access_token=access_token,
            token_type="bearer",
            user={
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "is_verified": user.is_verified,
            },
            subscription={
                "tier": subscription.tier,
                "trial_days_remaining": 7,
                "jobs_remaining": subscription.monthly_job_limit,
            },
            next_step="/onboarding/connect-drive",
            onboarding_complete=False,
        )

    except AuthError as e:
        # Friendly error message
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "registration_failed",
                "message": str(e),
                "action": "fix_and_retry",
            }
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in with email",
    description="Sign in to your account with email and password.",
)
async def login(
    data: LoginRequest,
    user_repo: UserRepository = Depends(get_user_repository),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Login with email/password.

    Returns:
        👋 Welcome back message with user profile
    """
    try:
        auth_service = get_auth_service(user_repo, subscription_repo)

        user = await auth_service.login_with_email(
            email=data.email,
            password=data.password,
        )

        # Get subscription
        subscription = subscription_repo.find_by_user_id(user.id)

        # Generate JWT access token
        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email
        )

        # Check if onboarding is complete
        onboarding_complete = user.has_drive_connected

        # Determine next step
        if not onboarding_complete:
            next_step = "/onboarding/connect-drive"
        else:
            next_step = "/dashboard"

        return AuthResponse(
            success=True,
            message=f"Welcome back, {user.full_name}! 👋",
            access_token=access_token,
            token_type="bearer",
            user={
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "is_verified": user.is_verified,
                "drive_connected": user.has_drive_connected,
            },
            subscription={
                "tier": subscription.tier,
                "jobs_remaining": subscription.remaining_jobs,
                "credits_remaining": subscription.remaining_credits,
            },
            next_step=next_step,
            onboarding_complete=onboarding_complete,
        )

    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "login_failed",
                "message": str(e),
                "action": "retry",
                "help_url": "/auth/forgot-password",
            }
        )


@router.get(
    "/google",
    summary="Sign in with Google",
    description="Start Google OAuth flow. One click, no passwords! 🚀",
)
async def google_oauth_start():
    """
    Initiate Google OAuth flow.

    UX: User clicks "Continue with Google" button

    Returns:
        Redirect to Google's OAuth consent screen
    """
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/drive.file",
        ],
    )

    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="offline",  # Get refresh token
        include_granted_scopes="true",
        prompt="consent",  # Force consent to get refresh token
    )

    logger.info("google_oauth_started", redirect_url=authorization_url)

    # Redirect user to Google
    return RedirectResponse(url=authorization_url)


@router.get(
    "/google/callback",
    summary="Google OAuth callback",
    description="Google redirects here after user grants permission.",
)
async def google_oauth_callback(
    code: str,
    state: Optional[str] = None,
    user_repo: UserRepository = Depends(get_user_repository),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Handle Google OAuth callback.

    UX Flow:
    1. Google redirects here with auth code
    2. We exchange code for tokens
    3. Create/login user
    4. Redirect to dashboard or onboarding

    Returns:
        Redirect to appropriate next step
    """
    try:
        auth_service = get_auth_service(user_repo, subscription_repo)

        user = await auth_service.login_with_google(auth_code=code)

        # Check if onboarding complete
        if user.has_drive_connected:
            # Existing user, go to dashboard
            redirect_url = f"{settings.FRONTEND_URL}/dashboard?welcome=back"
        else:
            # New user, go to onboarding
            redirect_url = f"{settings.FRONTEND_URL}/onboarding?welcome=true"

        logger.info(
            "google_oauth_success",
            user_id=user.id,
            is_new_user=not user.has_drive_connected,
        )

        return RedirectResponse(url=redirect_url)

    except AuthError as e:
        logger.error("google_oauth_callback_failed", error=str(e))

        # Redirect to error page with friendly message
        error_url = f"{settings.FRONTEND_URL}/auth/error?message={e}"
        return RedirectResponse(url=error_url)


@router.get(
    "/me",
    summary="Get current user",
    description="Get the currently logged-in user's profile.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    subscription_repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Get current user profile.

    Useful for:
    - Checking if user is still logged in
    - Getting latest profile data
    - Refreshing UI after profile updates

    Returns:
        User profile with subscription info
    """
    subscription = subscription_repo.find_by_user_id(current_user.id)

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "is_verified": current_user.is_verified,
            "drive_connected": current_user.has_drive_connected,
            "total_jobs_run": current_user.total_jobs_run,
            "member_since": current_user.created_at.isoformat(),
        },
        "subscription": {
            "tier": subscription.tier,
            "status": subscription.status,
            "jobs_remaining": subscription.remaining_jobs,
            "credits_remaining": subscription.remaining_credits,
            "trial_ends": subscription.trial_end.isoformat() if subscription.trial_end else None,
        },
        "onboarding_complete": current_user.has_drive_connected,
    }


@router.post(
    "/logout",
    summary="Log out",
    description="End your session.",
)
async def logout(
    current_user: User = Depends(get_current_user),
):
    """
    Logout current user.

    In a session-based system, this would clear the session.
    With JWT, frontend just discards the token.

    Returns:
        Success message
    """
    logger.info("user_logged_out", user_id=current_user.id)

    return {
        "success": True,
        "message": "See you next time! 👋",
        "redirect": "/login",
    }
