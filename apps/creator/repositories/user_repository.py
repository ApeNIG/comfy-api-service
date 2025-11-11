"""
User repository with custom queries
"""

from typing import Optional
from sqlalchemy.orm import Session

from apps.creator.models.domain import User
from apps.creator.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User-specific data access operations.

    Inherits standard CRUD from BaseRepository:
        - find_by_id(id) -> Optional[User]
        - find_all(skip, limit, order_by, descending) -> List[User]
        - create(**attrs) -> User
        - update(id, **attrs) -> Optional[User]
        - delete(id) -> bool
        - count(**filters) -> int
        - exists(**filters) -> bool
    """

    def __init__(self, db: Session):
        super().__init__(db, User)

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email address.

        Args:
            email: User's email

        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()

    def find_by_google_id(self, google_id: str) -> Optional[User]:
        """
        Find user by Google OAuth ID.

        Args:
            google_id: Google user ID

        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.google_id == google_id).first()

    def find_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Find all active users.

        Args:
            skip: Number of records to skip
            limit: Max records to return

        Returns:
            List of active users
        """
        return (
            self.db.query(User)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def find_users_with_drive_connected(
        self, skip: int = 0, limit: int = 100
    ) -> list[User]:
        """
        Find users who have connected Google Drive.

        Args:
            skip: Number of records to skip
            limit: Max records to return

        Returns:
            List of users with Drive connected
        """
        return (
            self.db.query(User)
            .filter(
                User.google_access_token.isnot(None),
                User.drive_folder_id.isnot(None),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def find_users_needing_token_refresh(self, limit: int = 100) -> list[User]:
        """
        Find users whose Google tokens are expiring soon.

        Used by background worker to proactively refresh tokens.

        Args:
            limit: Max records to return

        Returns:
            List of users needing token refresh
        """
        from datetime import datetime, timedelta

        threshold = datetime.utcnow() + timedelta(minutes=5)

        return (
            self.db.query(User)
            .filter(
                User.google_token_expires_at.isnot(None),
                User.google_token_expires_at <= threshold,
                User.google_refresh_token.isnot(None),
            )
            .limit(limit)
            .all()
        )

    def update_google_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: str | None = None,
    ) -> Optional[User]:
        """
        Update user's Google OAuth tokens (encrypted).

        Args:
            user_id: User UUID
            access_token: New access token (will be encrypted)
            refresh_token: New refresh token (will be encrypted)
            expires_at: Token expiration datetime

        Returns:
            Updated user or None if not found
        """
        attrs = {"google_access_token": access_token}

        if refresh_token:
            attrs["google_refresh_token"] = refresh_token

        if expires_at:
            attrs["google_token_expires_at"] = expires_at

        return self.update(user_id, **attrs)

    def update_drive_folders(
        self,
        user_id: str,
        input_folder_id: str,
        output_folder_id: str,
    ) -> Optional[User]:
        """
        Update user's Drive folder configuration.

        Args:
            user_id: User UUID
            input_folder_id: Drive folder ID for input files
            output_folder_id: Drive folder ID for output files

        Returns:
            Updated user or None if not found
        """
        return self.update(
            user_id,
            drive_folder_id=input_folder_id,
            drive_output_folder_id=output_folder_id,
        )

    def increment_job_count(self, user_id: str, credits: int = 1) -> Optional[User]:
        """
        Increment user's total job and credit counters.

        Args:
            user_id: User UUID
            credits: Number of credits consumed

        Returns:
            Updated user or None if not found
        """
        user = self.find_by_id(user_id)
        if not user:
            return None

        user.total_jobs_run += 1
        user.total_credits_used += credits

        self.db.flush()
        self.db.refresh(user)
        return user

    def record_login(self, user_id: str) -> Optional[User]:
        """
        Record user login timestamp.

        Args:
            user_id: User UUID

        Returns:
            Updated user or None if not found
        """
        from datetime import datetime

        return self.update(user_id, last_login_at=datetime.utcnow())
