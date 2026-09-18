"""LabelSegments use case — applies user labels to segments and computes nutrition."""

import logging
from typing import TypedDict

from app.application.services.food_item_nutrition import FoodItemNutritionService
from app.application.services.measurement_estimator import MeasurementEstimator
from app.application.services.nutrition_resolver import NutritionResolver
from app.domain.entities.food_item import FoodItem
from app.domain.entities.meal import Meal, SegmentLabelAssignment
from app.domain.exceptions import FoodNotFoundError, MealNotFoundError
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog
from app.domain.interfaces.meal_repository import MealRepository

logger = logging.getLogger(__name__)


class SegmentLabelAssignmentRequest(TypedDict):
    """A raw label assignment as received from the client.

    canonical_food_id is a string identifier that the use case resolves
    into a CanonicalFood entity before passing it to the domain.
    """

    canonical_food_id: str
    segment_ids: list[str]


class LabelSegmentsUseCase:
    """Applies user labels to segments.

    Segments sharing one label form one FoodItem (business rule 9).
    Nutrition is computed from the aggregated measurements of the
    assigned segments (business rule 10).

    Two modes share this workflow: labeling a fresh draft (the default)
    and replacing the labeling of an already-labeled meal, which the
    history edit flow uses.
    """

    def __init__(
        self,
        meal_repository: MealRepository,
        catalog: CanonicalFoodCatalog,
        nutrition_resolver: NutritionResolver,
        measurement_estimator: MeasurementEstimator,
    ) -> None:
        self._meal_repository = meal_repository
        self._catalog = catalog
        self._nutrition = FoodItemNutritionService(
            measurement_estimator,
            nutrition_resolver,
        )

    def execute(
        self,
        meal_id: str,
        assignments: list[SegmentLabelAssignmentRequest],
        replace: bool = False,
        name: str | None = None,
    ) -> Meal:
        """Assign labels to segments.

        Args:
            meal_id: The meal to label.
            assignments: Label groups; each assigns one canonical food
                to one or more segment ids.
            replace: When True, the meal's existing labeling is discarded
                and rebuilt from these assignments (edit flow). When
                False, only unlabeled segments may be assigned.
            name: When given, the meal is named in the same operation
                (an empty string clears the name).

        Returns:
            The corrected meal with food items and nutrition.

        Raises:
            MealNotFoundError: If the meal does not exist.
            FoodNotFoundError: If a referenced canonical food is unknown.
        """
        meal = self._meal_repository.get_by_id(meal_id)
        if meal is None:
            raise MealNotFoundError(f"Meal '{meal_id}' not found")

        translated = self._translate_assignments(assignments)
        created = (
            meal.replace_labels(translated)
            if replace
            else meal.label_segments(translated)
        )
        for item in created:
            self._estimate_and_resolve(item)

        if name is not None:
            meal.rename(name)

        meal.recalculate_nutrition()
        self._meal_repository.save(meal)
        logger.info(
            "Labels applied to meal %s: %d food items",
            meal_id,
            len(created),
        )
        return meal

    def _translate_assignments(
        self,
        assignments: list[SegmentLabelAssignmentRequest],
    ) -> list[SegmentLabelAssignment]:
        """Resolve string food identifiers into CanonicalFood entities."""
        translated: list[SegmentLabelAssignment] = []
        for request in assignments:
            canonical_food = self._catalog.get_by_id(
                request["canonical_food_id"]
            )
            if canonical_food is None:
                raise FoodNotFoundError(
                    f"Canonical food '{request['canonical_food_id']}' "
                    "not found"
                )
            translated.append(
                {
                    "canonical_food": canonical_food,
                    "segment_ids": request["segment_ids"],
                }
            )
        return translated

    def _estimate_and_resolve(self, item: FoodItem) -> None:
        """Estimate measurements and resolve nutrition for a labeled item."""
        self._nutrition.apply(item)
