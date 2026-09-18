"""ListMeals use case — provides the meal history."""

import logging

from app.domain.entities.meal import Meal
from app.domain.interfaces.meal_repository import MealRepository

logger = logging.getLogger(__name__)


class ListMealsUseCase:
    """Lists stored meals, newest first."""

    def __init__(self, meal_repository: MealRepository) -> None:
        self._meal_repository = meal_repository

    def execute(self, limit: int = 20, offset: int = 0) -> list[Meal]:
        """Return one page of stored meals.

        Args:
            limit: Maximum number of meals to return.
            offset: Number of meals to skip.

        Returns:
            Meals ordered newest first.
        """
        return self._meal_repository.list_recent(limit=limit, offset=offset)
