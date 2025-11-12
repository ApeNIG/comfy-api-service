"""
User repository with custom queries
"""

from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from apps.creator.models import User
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

    def find_by_api_key(self, api_key: str) -> Optional[User]:
        """
        Find user by API key.

        Args:
            api_key: User's API key

        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.api_key == api_key).first()

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

    def find_by_reset_token(self, token: str) -> Optional[User]:
        """
        Find user by password reset token.

        Args:
            token: Password reset token

        Returns:
            User instance or None if not found/expired
        """
        now = datetime.utcnow()
        return (
            self.db.query(User)
            .filter(
                User.reset_token == token,
                User.reset_token_expires.isnot(None),
                User.reset_token_expires > now,
            )
            .first()
        )

    def increment_monthly_usage(self, user_id: UUID) -> Optional[User]:
        """
        Increment user's monthly generation count and total.

        Args:
            user_id: User UUID

        Returns:
            Updated user or None if not found
        """
        user = self.find_by_id(user_id)
        if not user:
            return None

        user.monthly_generation_count += 1
        user.total_generations += 1

        self.db.flush()
        self.db.refresh(user)
        return user

    def record_login(self, user_id: UUID) -> Optional[User]:
        """
        Record user login timestamp and increment login count.

        Args:
            user_id: User UUID

        Returns:
            Updated user or None if not found
        """
        user = self.find_by_id(user_id)
        if not user:
            return None

        user.last_login_at = datetime.utcnow()
        user.login_count += 1

        self.db.flush()
        self.db.refresh(user)
        return user
