"""DiscardSegments use case — drops crops the user does not want."""

import logging

from app.application.services.food_item_nutrition import FoodItemNutritionService
from app.application.services.measurement_estimator import MeasurementEstimator
from app.application.services.nutrition_resolver import NutritionResolver
from app.domain.entities.meal import Meal
from app.domain.exceptions import MealNotFoundError
from app.domain.interfaces.meal_repository import MealRepository
from app.domain.interfaces.storage_provider import StorageProvider

logger = logging.getLogger(__name__)


class DiscardSegmentsUseCase:
    """Removes segments that should not be part of the meal.

    Covers bad segmentations and foods the catalog cannot describe. Crop
    images are deleted with them, and only the food items that lost a
    segment are re-measured — other items keep any corrected weight the
    user set earlier.
    """

    def __init__(
        self,
        meal_repository: MealRepository,
        storage_provider: StorageProvider,
        nutrition_resolver: NutritionResolver,
        measurement_estimator: MeasurementEstimator,
    ) -> None:
        self._meal_repository = meal_repository
        self._storage_provider = storage_provider
        self._nutrition = FoodItemNutritionService(
            measurement_estimator,
            nutrition_resolver,
        )

    def execute(self, meal_id: str, segment_ids: list[str]) -> Meal:
        """Discard one or more segments and return the updated meal.

        Args:
            meal_id: The meal the segments belong to.
            segment_ids: The segments to discard.

        Returns:
            The meal without those segments.

        Raises:
            MealNotFoundError: If the meal does not exist.
            ValueError: If no ids are given, an id is unknown, or the
                meal is finalized. The meal is left untouched when
                validation fails.
        """
        if not segment_ids:
            raise ValueError("At least one segment id is required")
        meal = self._meal_repository.get_by_id(meal_id)
        if meal is None:
            raise MealNotFoundError(f"Meal '{meal_id}' not found")

        known_ids = {segment.segment_id for segment in meal.segments}
        unknown = [sid for sid in segment_ids if sid not in known_ids]
        if unknown:
            raise ValueError(
                f"Segment(s) not found in meal: {', '.join(unknown)}"
            )

        affected_items = self._affected_item_ids(meal, segment_ids)
        discarded = [
            meal.discard_segment(segment_id) for segment_id in segment_ids
        ]
        for segment in discarded:
            self._delete_crop(segment.crop_image_ref)

        for item in meal.food_items:
            if (
                item.food_item_id in affected_items
                and item.canonical_food is not None
            ):
                self._nutrition.apply(item)
        meal.recalculate_nutrition()
        self._meal_repository.save(meal)
        logger.info(
            "Discarded %d segment(s) from meal %s",
            len(discarded),
            meal_id,
        )
        return meal

    @staticmethod
    def _affected_item_ids(meal: Meal, segment_ids: list[str]) -> set[str]:
        """Food items containing any of the segments about to be discarded."""
        targets = set(segment_ids)
        return {
            item.food_item_id
            for item in meal.food_items
            if any(
                segment.segment_id in targets for segment in item.segments
            )
        }

    def _delete_crop(self, crop_ref: str) -> None:
        if not crop_ref:
            return
        try:
            self._storage_provider.delete(crop_ref)
        except OSError as exc:
            logger.warning(
                "Failed to delete crop '%s': %s",
                crop_ref,
                exc,
            )
