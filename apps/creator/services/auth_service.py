"""
Authentication service with delightful UX

This isn't just auth - it's the first impression users get.
Every error message is helpful, not scary.
Every success feels like a small win.

UX Principles:
- Google OAuth as primary (no password fatigue)
- Clear, friendly error messages
- Automatic profile setup
- Smart defaults everywhere
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets

from apps.creator.repositories import UserRepository
from apps.creator.models import User
from apps.creator.models.user import UserRole, SubscriptionTier, SubscriptionStatus
from apps.creator.utils.password import hash_password, verify_password
from apps.creator.utils.jwt import create_access_token
from apps.shared.services.email import get_email_service
from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


class AuthError(Exception):
    """
    Friendly authentication errors.

    UX Note: Error messages are shown to users, so make them helpful!
    """
    pass


class AuthService:
    """
    Authentication service with excellent UX.

    Features:
    - Google OAuth (primary method - no password fatigue!)
    - Email/password (fallback)
    - Automatic profile setup
    - Free trial on signup
    - Welcome email with getting started guide

    UX Focus:
    - Every error message helps the user fix the problem
    - Success states feel like wins
    - Smart defaults reduce decisions
    """

    def __init__(
        self,
        user_repo: UserRepository,
    ):
        self.user_repo = user_repo
        self.email_service = get_email_service()

    async def register_with_email(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> Tuple[User, str]:
        """
        Register new user with email/password.

        UX Flow:
        1. Create account
        2. Send verification email
        3. Create free trial subscription
        4. Return user + verification token

        Args:
            email: User's email (will be verified)
            password: Plain text password (we'll hash it)
            full_name: Optional display name

        Returns:
            Tuple of (User, verification_token)

        Raises:
            AuthError: With helpful message if something goes wrong

        Example:
            >>> user, token = await auth.register_with_email(
            ...     "user@example.com",
            ...     "secure_password",
            ...     "Jane Doe"
            ... )
            >>> print(f"Welcome {user.full_name}! Check your email.")
        """
        # Validate email isn't taken
        existing = self.user_repo.find_by_email(email)
        if existing:
            raise AuthError(
                "This email is already registered. "
                "Try logging in, or use 'Forgot Password' if you don't remember it."
            )

        # Hash password using bcrypt
        hashed_password = hash_password(password)

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)

        # Create user with 7-day trial
        trial_end = datetime.utcnow() + timedelta(days=7)

        user = self.user_repo.create(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name or email.split("@")[0],  # Smart default: use email prefix
            is_active=True,
            is_verified=False,
            role=UserRole.USER.value,
            # Subscription data (embedded in User model)
            subscription_tier=SubscriptionTier.FREE.value,
            subscription_status=SubscriptionStatus.ACTIVE.value,
            trial_ends_at=trial_end,
            monthly_generation_count=0,
            total_generations=0,
        )

        # Send welcome email with verification link
        verification_link = f"{settings.FRONTEND_URL}/verify?token={verification_token}"

        await self.email_service.send_verification_email(
            to=user.email,
            verification_link=verification_link,
        )

        logger.info(
            "user_registered",
            user_id=user.id,
            email=user.email,
            trial_days=7,
        )

        return user, verification_token

    async def login_with_email(
        self,
        email: str,
        password: str,
    ) -> User:
        """
        Login with email/password.

        Args:
            email: User's email
            password: Plain text password

        Returns:
            User object if login successful

        Raises:
            AuthError: With helpful message if login fails

        Example:
            >>> user = await auth.login_with_email("user@example.com", "password")
            >>> print(f"Welcome back, {user.full_name}!")
        """
        # Find user
        user = self.user_repo.find_by_email(email)

        if not user or not user.hashed_password:
            raise AuthError(
                "We couldn't find an account with that email. "
                "Double-check the spelling, or sign up if you're new here!"
            )

        # Verify password using bcrypt
        if not verify_password(password, user.hashed_password):
            raise AuthError(
                "That password doesn't match our records. "
                "Try again, or use 'Forgot Password' to reset it."
            )

        # Check if account is active
        if not user.is_active:
            raise AuthError(
                "Your account has been deactivated. "
                "Contact support if you think this is a mistake."
            )

        # Check trial expiration
        if user.trial_ends_at and user.trial_ends_at < datetime.utcnow():
            if user.subscription_tier == SubscriptionTier.FREE:
                logger.warning("trial_expired", user_id=user.id, email=user.email)
                # Don't block login, but they'll see limited functionality

        # Record login
        self.user_repo.record_login(user.id)

        logger.info("user_logged_in", user_id=user.id, email=user.email)

        return user

    async def request_password_reset(self, email: str) -> Optional[str]:
        """
        Generate password reset token and send reset email.

        Args:
            email: User's email address

        Returns:
            Reset token if user found, None otherwise

        Example:
            >>> token = await auth.request_password_reset("user@example.com")
            >>> if token:
            ...     print("Reset email sent!")
        """
        user = self.user_repo.find_by_email(email)

        if not user:
            # Don't reveal if email exists (security best practice)
            logger.info("password_reset_requested_invalid_email", email=email)
            return None

        # Generate reset token (1-hour expiration)
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        # Store token in user record
        self.user_repo.update(
            user.id,
            reset_token=reset_token,
            reset_token_expires=expires_at,
        )

        # Send reset email
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        await self.email_service.send_password_reset_email(
            to=user.email,
            reset_link=reset_link,
        )

        logger.info("password_reset_requested", user_id=user.id, email=user.email)

        return reset_token

    async def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset user's password with reset token.

        Args:
            token: Password reset token from email
            new_password: New password to set

        Returns:
            Updated user

        Raises:
            AuthError: If token is invalid or expired

        Example:
            >>> user = await auth.reset_password(token, "new_password_123")
            >>> print("Password reset successfully!")
        """
        user = self.user_repo.find_by_reset_token(token)

        if not user:
            raise AuthError(
                "This reset link is invalid or has expired. "
                "Please request a new password reset."
            )

        # Hash new password with bcrypt
        hashed_password = hash_password(new_password)

        # Update password and clear reset token
        self.user_repo.update(
            user.id,
            hashed_password=hashed_password,
            reset_token=None,
            reset_token_expires=None,
        )

        logger.info("password_reset_completed", user_id=user.id, email=user.email)

        return user

    def mark_onboarding_complete(self, user: User) -> User:
        """
        Mark user's onboarding as complete.

        Args:
            user: User to update

        Returns:
            Updated user

        Example:
            >>> user = auth_service.mark_onboarding_complete(user)
            >>> assert user.onboarding_completed
        """
        self.user_repo.update(user.id, onboarding_completed=True)

        logger.info("onboarding_completed", user_id=user.id, email=user.email)

        # Refresh user object
        return self.user_repo.find_by_id(user.id)

    def check_trial_status(self, user: User) -> dict:
        """
        Check user's trial status and return info.

        Args:
            user: User to check

        Returns:
            Dict with trial status information

        Example:
            >>> status = auth_service.check_trial_status(user)
            >>> if status["is_trial_active"]:
            ...     print(f"Trial expires in {status['days_remaining']} days")
        """
        now = datetime.utcnow()

        if not user.trial_ends_at:
            return {
                "is_trial_active": False,
                "days_remaining": 0,
                "trial_expired": False,
            }

        is_active = user.trial_ends_at > now
        days_remaining = max(0, (user.trial_ends_at - now).days)

        return {
            "is_trial_active": is_active,
            "days_remaining": days_remaining,
            "trial_expired": user.trial_ends_at <= now,
            "trial_end_date": user.trial_ends_at.isoformat(),
        }

    def generate_access_token(self, user: User) -> str:
        """
        Generate JWT access token for user.

        Args:
            user: User to generate token for

        Returns:
            JWT access token (7-day expiration)

        Example:
            >>> token = auth_service.generate_access_token(user)
            >>> print(f"Token: {token}")
        """
        return create_access_token(user.id, user.email)


def get_auth_service(
    user_repo: UserRepository,
) -> AuthService:
    """
    Factory for AuthService.

    Usage in routes:
        auth_service = get_auth_service(user_repo)
    """
    return AuthService(user_repo)
