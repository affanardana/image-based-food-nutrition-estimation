"""GetMeal use case — retrieves a meal by its identifier."""

from app.domain.entities.meal import Meal
from app.domain.exceptions import MealNotFoundError
from app.domain.interfaces.meal_repository import MealRepository


class GetMealUseCase:
    """Retrieves a previously analyzed meal."""

    def __init__(self, meal_repository: MealRepository) -> None:
        self._meal_repository = meal_repository

    def execute(self, meal_id: str) -> Meal:
        """Retrieve a meal by ID.

        Args:
            meal_id: The meal identifier.

        Returns:
            The meal aggregate.

        Raises:
            MealNotFoundError: If the meal does not exist.
        """
        meal = self._meal_repository.get_by_id(meal_id)
        if meal is None:
            raise MealNotFoundError(f"Meal '{meal_id}' not found")
        return meal
