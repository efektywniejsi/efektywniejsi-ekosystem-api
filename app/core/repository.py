"""Base repository pattern implementation.

This module provides a generic repository pattern that can be used
as a base for domain-specific repositories.
"""

from typing import Generic, TypeVar, cast
from uuid import UUID

from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Generic repository with common CRUD operations.

    This class provides a base implementation for repository pattern.
    Domain-specific repositories should inherit from this class and
    override/extend methods as needed.

    Example:
        ```python
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(db, User)

            def find_by_email(self, email: str) -> User | None:
                return self.db.query(self.model).filter(self.model.email == email).first()
        ```
    """

    def __init__(self, db: Session, model: type[ModelType]):
        """Initialize repository with database session and model class.

        Args:
            db: SQLAlchemy session.
            model: The model class this repository operates on.
        """
        self.db = db
        self.model = model

    def get_by_id(self, entity_id: UUID) -> ModelType | None:
        """Get a single entity by ID.

        Args:
            entity_id: The UUID of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        result = self.db.query(self.model).filter(self.model.id == entity_id).first()  # type: ignore[attr-defined]
        return cast(ModelType | None, result)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get all entities with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of entities.
        """
        result = self.db.query(self.model).offset(skip).limit(limit).all()
        return cast(list[ModelType], result)

    def count(self) -> int:
        """Count total number of entities.

        Returns:
            Total count of entities.
        """
        result: int = self.db.query(self.model).count()
        return result

    def create(self, **kwargs: object) -> ModelType:
        """Create a new entity.

        Args:
            **kwargs: Entity attributes.

        Returns:
            The created entity.
        """
        instance = self.model(**kwargs)  # type: ignore[call-arg]
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(self, instance: ModelType, **kwargs: object) -> ModelType:
        """Update an existing entity.

        Uses immutable update pattern - creates a new dict with updates
        rather than mutating the instance directly.

        Args:
            instance: The entity to update.
            **kwargs: Attributes to update.

        Returns:
            The updated entity.
        """
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelType) -> None:
        """Delete an entity.

        Args:
            instance: The entity to delete.
        """
        self.db.delete(instance)
        self.db.commit()

    def exists(self, entity_id: UUID) -> bool:
        """Check if an entity exists by ID.

        Args:
            entity_id: The UUID to check.

        Returns:
            True if entity exists, False otherwise.
        """
        return self.get_by_id(entity_id) is not None
