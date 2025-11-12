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
from uuid import UUID

from apps.creator.services.auth_service import AuthService, AuthError, get_auth_service
from apps.creator.repositories import UserRepository
from apps.creator.dependencies import get_user_repository, get_current_user
from apps.creator.models import User
from apps.creator.utils.jwt import create_access_token
from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

router = APIRouter(tags=["🔐 Authentication"])


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


class ForgotPasswordRequest(BaseModel):
    """Request password reset email."""
    email: EmailStr = Field(..., description="Email address")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "jane@example.com"
            }
        }


class ResetPasswordRequest(BaseModel):
    """Reset password with token from email."""
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123token",
                "new_password": "new_secure_password_456"
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
        auth_service = get_auth_service(user_repo)

        user, verification_token = await auth_service.register_with_email(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )

        # Generate JWT access token
        access_token = create_access_token(user.id, user.email)

        # Get trial status
        trial_status = auth_service.check_trial_status(user)

        # Calculate jobs remaining based on tier
        from apps.shared.models.enums import SubscriptionTier
        tier_limits = {
            SubscriptionTier.FREE: 10,
            SubscriptionTier.CREATOR: 100,
            SubscriptionTier.STUDIO: float('inf')
        }
        limit = tier_limits.get(user.subscription_tier, 10)
        jobs_remaining = max(0, int(limit) - user.monthly_generation_count) if limit != float('inf') else 999999

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
                "tier": user.subscription_tier.value if hasattr(user.subscription_tier, 'value') else str(user.subscription_tier),
                "trial_days_remaining": trial_status["days_remaining"],
                "jobs_remaining": jobs_remaining,
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
):
    """
    Login with email/password.

    Returns:
        👋 Welcome back message with user profile
    """
    try:
        auth_service = get_auth_service(user_repo)

        user = await auth_service.login_with_email(
            email=data.email,
            password=data.password,
        )

        # Generate JWT access token
        access_token = create_access_token(user.id, user.email)

        # Get trial status
        trial_status = auth_service.check_trial_status(user)

        # Calculate jobs remaining based on tier
        from apps.shared.models.enums import SubscriptionTier
        tier_limits = {
            SubscriptionTier.FREE: 10,
            SubscriptionTier.CREATOR: 100,
            SubscriptionTier.STUDIO: float('inf')
        }
        limit = tier_limits.get(user.subscription_tier, 10)
        jobs_remaining = max(0, int(limit) - user.monthly_generation_count) if limit != float('inf') else 999999

        # Check if onboarding is complete
        onboarding_complete = user.onboarding_completed

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
            },
            subscription={
                "tier": user.subscription_tier.value if hasattr(user.subscription_tier, 'value') else str(user.subscription_tier),
                "trial_days_remaining": trial_status["days_remaining"],
                "jobs_remaining": jobs_remaining,
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


@router.post(
    "/forgot-password",
    summary="Request password reset",
    description="Send password reset email to user.",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Request password reset email.

    Security note: Always returns success even if email doesn't exist
    (don't reveal which emails are registered).

    Returns:
        Success message
    """
    try:
        auth_service = get_auth_service(user_repo)

        await auth_service.request_password_reset(email=data.email)

        return {
            "success": True,
            "message": "If that email is registered, you'll receive a password reset link shortly. Check your inbox!",
        }

    except Exception as e:
        logger.error("password_reset_request_failed", error=str(e))
        # Still return success (don't reveal errors)
        return {
            "success": True,
            "message": "If that email is registered, you'll receive a password reset link shortly. Check your inbox!",
        }


@router.post(
    "/reset-password",
    summary="Reset password with token",
    description="Complete password reset with token from email.",
)
async def reset_password(
    data: ResetPasswordRequest,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """
    Reset password with token from email.

    Returns:
        Success message
    """
    try:
        auth_service = get_auth_service(user_repo)

        user = await auth_service.reset_password(
            token=data.token,
            new_password=data.new_password,
        )

        return {
            "success": True,
            "message": "Password reset successfully! You can now log in with your new password.",
            "redirect": "/login",
        }

    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "reset_failed",
                "message": str(e),
                "action": "request_new_reset",
            }
        )


@router.get(
    "/me",
    summary="Get current user",
    description="Get the currently logged-in user's profile.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
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
    auth_service = get_auth_service(user_repo)
    trial_status = auth_service.check_trial_status(current_user)

    # Calculate jobs remaining based on tier
    from apps.shared.models.enums import SubscriptionTier
    tier_limits = {
        SubscriptionTier.FREE: 10,
        SubscriptionTier.CREATOR: 100,
        SubscriptionTier.STUDIO: float('inf')
    }
    limit = tier_limits.get(current_user.subscription_tier, 10)
    jobs_remaining = max(0, int(limit) - current_user.monthly_generation_count) if limit != float('inf') else 999999

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "is_verified": current_user.is_verified,
            "total_generations": current_user.total_generations,
            "member_since": current_user.created_at.isoformat(),
        },
        "subscription": {
            "tier": current_user.subscription_tier.value if hasattr(current_user.subscription_tier, 'value') else str(current_user.subscription_tier),
            "status": current_user.subscription_status.value if hasattr(current_user.subscription_status, 'value') else str(current_user.subscription_status),
            "jobs_remaining": jobs_remaining,
            "trial_days_remaining": trial_status["days_remaining"],
            "trial_active": trial_status["is_trial_active"],
            "trial_end_date": trial_status.get("trial_end_date"),
        },
        "onboarding_complete": current_user.onboarding_completed,
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
