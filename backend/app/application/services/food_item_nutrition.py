"""Shared estimation and nutrition resolution for labeled food items.

One food item is always measured and resolved the same way — after
labeling, after a re-label, and after a segment is discarded. Keeping it
here means every path computes nutrition identically.
"""

from app.application.services.measurement_estimator import MeasurementEstimator
from app.application.services.nutrition_resolver import NutritionResolver
from app.domain.entities.food_item import FoodItem


class FoodItemNutritionService:
    """Estimates measurements and resolves nutrition for food items."""

    def __init__(
        self,
        measurement_estimator: MeasurementEstimator,
        nutrition_resolver: NutritionResolver,
    ) -> None:
        self._measurement_estimator = measurement_estimator
        self._nutrition_resolver = nutrition_resolver

    def apply(self, item: FoodItem) -> None:
        """Estimate and resolve one food item in place.

        Raises:
            ValueError: If the item has no canonical food.
        """
        if item.canonical_food is None:
            raise ValueError(
                f"Food item '{item.food_item_id}' has no canonical food"
            )
        item.measurement = self._measurement_estimator.estimate(
            item.canonical_food,
            item.segments,
        )
        item.set_nutrition_profile(
            self._nutrition_resolver.resolve(
                item.canonical_food,
                item.measurement,
            )
        )
