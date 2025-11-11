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
import hashlib

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.creator.repositories import UserRepository, SubscriptionRepository
from apps.creator.models.domain import User, Subscription
from apps.shared.models.enums import UserRole, SubscriptionTier, SubscriptionStatus
from apps.shared.services.encryption import get_encryptor
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
        subscription_repo: SubscriptionRepository,
    ):
        self.user_repo = user_repo
        self.subscription_repo = subscription_repo
        self.encryptor = get_encryptor()
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

        # Hash password
        password_hash = self._hash_password(password)

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)

        # Create user
        user = self.user_repo.create(
            email=email,
            password_hash=password_hash,
            full_name=full_name or email.split("@")[0],  # Smart default: use email prefix
            is_active=True,
            is_verified=False,
            role=UserRole.USER.value,
            total_jobs_run=0,
            total_credits_used=0,
        )

        # Create free trial subscription (7 days)
        trial_end = datetime.utcnow() + timedelta(days=7)

        self.subscription_repo.create(
            user_id=user.id,
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            trial_start=datetime.utcnow(),
            trial_end=trial_end,
            monthly_job_limit=10,  # Free tier: 10 jobs/month
            monthly_credit_limit=100,
            jobs_used_this_period=0,
            credits_used_this_period=0,
            price_currency="USD",
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

        if not user or not user.password_hash:
            raise AuthError(
                "We couldn't find an account with that email. "
                "Double-check the spelling, or sign up if you're new here!"
            )

        # Verify password
        if not self._verify_password(password, user.password_hash):
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

        # Record login
        self.user_repo.record_login(user.id)

        logger.info("user_logged_in", user_id=user.id, email=user.email)

        return user

    async def login_with_google(
        self,
        auth_code: str,
    ) -> User:
        """
        Login or register with Google OAuth.

        This is the PREFERRED method - no passwords to remember!

        UX Flow:
        1. User clicks "Continue with Google"
        2. Google handles authentication
        3. We get auth_code
        4. Exchange code for tokens
        5. Get user profile from Google
        6. Create account if new, or login if existing
        7. Store encrypted tokens for Drive access

        Args:
            auth_code: OAuth authorization code from Google

        Returns:
            User object (created or existing)

        Raises:
            AuthError: With helpful message if OAuth fails

        Example:
            >>> # User clicked "Continue with Google" and was redirected back
            >>> user = await auth.login_with_google(auth_code)
            >>> print(f"Welcome, {user.full_name}!")
        """
        try:
            # Exchange auth code for tokens
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
                    "https://www.googleapis.com/auth/drive.file",  # Access user's files
                ],
            )

            flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
            flow.fetch_token(code=auth_code)

            credentials = flow.credentials

            # Get user profile from Google
            service = build("oauth2", "v2", credentials=credentials)
            user_info = service.userinfo().get().execute()

            google_id = user_info.get("id")
            email = user_info.get("email")
            full_name = user_info.get("name")
            avatar_url = user_info.get("picture")

            # Find or create user
            user = self.user_repo.find_by_google_id(google_id)

            if user:
                # Existing user - update tokens and profile
                token_expiry = datetime.utcnow() + timedelta(seconds=3600)

                self.user_repo.update_google_tokens(
                    user_id=user.id,
                    access_token=self.encryptor.encrypt(credentials.token),
                    refresh_token=self.encryptor.encrypt(credentials.refresh_token) if credentials.refresh_token else None,
                    expires_at=token_expiry,
                )

                # Update profile if changed
                self.user_repo.update(
                    user.id,
                    full_name=full_name,
                    avatar_url=avatar_url,
                )

                self.user_repo.record_login(user.id)

                logger.info("user_logged_in_google", user_id=user.id, email=email)

            else:
                # New user - create account with Google profile
                token_expiry = datetime.utcnow() + timedelta(seconds=3600)

                user = self.user_repo.create(
                    email=email,
                    google_id=google_id,
                    google_access_token=self.encryptor.encrypt(credentials.token),
                    google_refresh_token=self.encryptor.encrypt(credentials.refresh_token) if credentials.refresh_token else None,
                    google_token_expires_at=token_expiry,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    is_active=True,
                    is_verified=True,  # Google verified their email
                    role=UserRole.USER.value,
                    total_jobs_run=0,
                    total_credits_used=0,
                )

                # Create free trial subscription
                trial_end = datetime.utcnow() + timedelta(days=7)

                self.subscription_repo.create(
                    user_id=user.id,
                    tier=SubscriptionTier.FREE.value,
                    status=SubscriptionStatus.ACTIVE.value,
                    trial_start=datetime.utcnow(),
                    trial_end=trial_end,
                    monthly_job_limit=10,
                    monthly_credit_limit=100,
                    jobs_used_this_period=0,
                    credits_used_this_period=0,
                    price_currency="USD",
                )

                logger.info(
                    "user_registered_google",
                    user_id=user.id,
                    email=email,
                    trial_days=7,
                )

            return user

        except HttpError as e:
            logger.error("google_oauth_failed", error=str(e), exc_info=True)
            raise AuthError(
                "Something went wrong connecting to Google. "
                "Please try again, or contact support if this keeps happening."
            )

    async def refresh_google_token(self, user: User) -> str:
        """
        Refresh expired Google access token.

        Google tokens expire after 1 hour. This refreshes them automatically.

        Args:
            user: User with expired token

        Returns:
            New access token

        Raises:
            AuthError: If refresh fails
        """
        if not user.google_refresh_token:
            raise AuthError("Cannot refresh token - no refresh token available")

        try:
            # Decrypt refresh token
            refresh_token = self.encryptor.decrypt(user.google_refresh_token)

            # Create credentials and refresh
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
            )

            credentials.refresh(Request())

            # Store new token
            token_expiry = datetime.utcnow() + timedelta(seconds=3600)

            self.user_repo.update_google_tokens(
                user_id=user.id,
                access_token=self.encryptor.encrypt(credentials.token),
                expires_at=token_expiry,
            )

            logger.info("google_token_refreshed", user_id=user.id)

            return credentials.token

        except Exception as e:
            logger.error("token_refresh_failed", user_id=user.id, error=str(e))
            raise AuthError(
                "We couldn't refresh your Google connection. "
                "Please reconnect your Drive to continue."
            )

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256 + salt."""
        # In production, use bcrypt or argon2
        # This is simplified for MVP
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${hashed}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            salt, hashed = password_hash.split("$")
            test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return test_hash == hashed
        except:
            return False


def get_auth_service(
    user_repo: UserRepository,
    subscription_repo: SubscriptionRepository,
) -> AuthService:
    """
    Factory for AuthService.

    Usage in routes:
        auth_service = get_auth_service(user_repo, subscription_repo)
    """
    return AuthService(user_repo, subscription_repo)
