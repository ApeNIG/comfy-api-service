"""
Base repository with common CRUD operations

All repositories should inherit from this to get standard operations.
"""

from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID

from apps.shared.models.base import BaseModel

# Generic type for models
ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with generic CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(db, User)

            # Add custom queries
            def find_by_email(self, email: str) -> Optional[User]:
                return self.db.query(self.model).filter_by(email=email).first()
    """

    def __init__(self, db: Session, model: Type[ModelType]):
        """
        Initialize repository.

        Args:
            db: SQLAlchemy session
            model: Model class (e.g., User, Job)
        """
        self.db = db
        self.model = model

    def find_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Find record by ID.

        Args:
            id: Record UUID

        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()

    def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> List[ModelType]:
        """
        Find all records with pagination.

        Args:
            skip: Number of records to skip
            limit: Max records to return
            order_by: Column name to sort by
            descending: Sort descending if True

        Returns:
            List of model instances
        """
        query = self.db.query(self.model)

        # Order by
        if hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(column.desc() if descending else column)

        return query.offset(skip).limit(limit).all()

    def find_by(self, **filters) -> List[ModelType]:
        """
        Find records matching filters.

        Args:
            **filters: Column=value pairs

        Returns:
            List of matching records

        Usage:
            users = repo.find_by(email="user@example.com", is_active=True)
        """
        return self.db.query(self.model).filter_by(**filters).all()

    def find_one_by(self, **filters) -> Optional[ModelType]:
        """
        Find single record matching filters.

        Args:
            **filters: Column=value pairs

        Returns:
            Model instance or None

        Usage:
            user = repo.find_one_by(email="user@example.com")
        """
        return self.db.query(self.model).filter_by(**filters).first()

    def create(self, **attrs) -> ModelType:
        """
        Create new record.

        Args:
            **attrs: Model attributes

        Returns:
            Created model instance

        Usage:
            user = repo.create(email="user@example.com", name="John")
        """
        instance = self.model(**attrs)
        self.db.add(instance)
        self.db.flush()  # Get ID without committing
        self.db.refresh(instance)
        return instance

    def update(self, id: UUID, **attrs) -> Optional[ModelType]:
        """
        Update record by ID.

        Args:
            id: Record UUID
            **attrs: Attributes to update

        Returns:
            Updated model instance or None if not found

        Usage:
            user = repo.update(user_id, name="Jane", email="jane@example.com")
        """
        instance = self.find_by_id(id)
        if not instance:
            return None

        for key, value in attrs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        self.db.flush()
        self.db.refresh(instance)
        return instance

    def delete(self, id: UUID) -> bool:
        """
        Delete record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found

        Usage:
            success = repo.delete(user_id)
        """
        instance = self.find_by_id(id)
        if not instance:
            return False

        self.db.delete(instance)
        self.db.flush()
        return True

    def count(self, **filters) -> int:
        """
        Count records matching filters.

        Args:
            **filters: Column=value pairs

        Returns:
            Number of matching records

        Usage:
            active_users = repo.count(is_active=True)
        """
        query = self.db.query(self.model)
        if filters:
            query = query.filter_by(**filters)
        return query.count()

    def exists(self, **filters) -> bool:
        """
        Check if records exist matching filters.

        Args:
            **filters: Column=value pairs

        Returns:
            True if exists, False otherwise

        Usage:
            email_taken = repo.exists(email="user@example.com")
        """
        return self.count(**filters) > 0

    def bulk_create(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records at once.

        Args:
            items: List of attribute dictionaries

        Returns:
            List of created instances

        Usage:
            users = repo.bulk_create([
                {"email": "user1@example.com", "name": "User 1"},
                {"email": "user2@example.com", "name": "User 2"},
            ])
        """
        instances = [self.model(**attrs) for attrs in items]
        self.db.bulk_save_objects(instances, return_defaults=True)
        self.db.flush()
        return instances
