"""MealRepository interface — contract for meal persistence."""

from abc import ABC, abstractmethod

from app.domain.entities.meal import Meal


class MealRepository(ABC):
    """Interface for persisting and retrieving Meal aggregates.

    Implementations may use PostgreSQL, SQLite, or any other storage.
    The domain layer must never depend on the storage technology.
    """

    @abstractmethod
    def save(self, meal: Meal) -> None:
        """Persist a meal aggregate (insert or update)."""
        ...

    @abstractmethod
    def get_by_id(self, meal_id: str) -> Meal | None:
        """Retrieve a meal by its unique identifier.

        Returns None if the meal does not exist.
        """
        ...

    @abstractmethod
    def delete(self, meal_id: str) -> None:
        """Remove a meal by its unique identifier."""
        ...

    @abstractmethod
    def list_recent(self, limit: int = 20, offset: int = 0) -> list[Meal]:
        """Return stored meals, newest first.

        Args:
            limit: Maximum number of meals to return.
            offset: Number of meals to skip (for paging).

        Returns:
            Fully populated Meal aggregates, most recently created first.
        """
        ...

    @abstractmethod
    def exists(self, meal_id: str) -> bool:
        """Check whether a meal with the given ID exists."""
        ...
