"""DeleteMeal use case — removes a meal and its stored image."""

import logging

from app.domain.entities.meal import Meal
from app.domain.exceptions import MealNotFoundError
from app.domain.interfaces.meal_repository import MealRepository
from app.domain.interfaces.storage_provider import StorageProvider

logger = logging.getLogger(__name__)


class DeleteMealUseCase:
    """Deletes an existing meal along with its stored image."""

    def __init__(
        self,
        meal_repository: MealRepository,
        storage_provider: StorageProvider,
    ) -> None:
        self._meal_repository = meal_repository
        self._storage_provider = storage_provider

    def execute(self, meal_id: str) -> None:
        """Delete a meal by ID.

        Args:
            meal_id: The meal identifier.

        Raises:
            MealNotFoundError: If the meal does not exist.
        """
        meal = self._meal_repository.get_by_id(meal_id)
        if meal is None:
            raise MealNotFoundError(f"Meal '{meal_id}' not found")

        self._delete_stored_files(meal)
        self._meal_repository.delete(meal_id)
        logger.info("Meal deleted: %s", meal_id)

    def _delete_stored_files(self, meal: Meal) -> None:
        """Remove the meal image and its crops, ignoring missing files."""
        references = [meal.image_path]
        references.extend(
            segment.crop_image_ref for segment in meal.segments
        )
        for reference in references:
            if not reference:
                continue
            try:
                self._storage_provider.delete(reference)
            except OSError as exc:
                logger.warning(
                    "Failed to delete stored file '%s': %s",
                    reference,
                    exc,
                )
