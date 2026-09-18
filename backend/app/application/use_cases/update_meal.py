"""UpdateMeal use case — applies user corrections and recalculates nutrition."""

import logging
from typing import TypedDict

from app.application.services.nutrition_resolver import NutritionResolver
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.food_item import FoodItem
from app.domain.entities.meal import FoodItemCorrection, Meal
from app.domain.exceptions import FoodNotFoundError, MealNotFoundError
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog
from app.domain.interfaces.meal_repository import MealRepository

logger = logging.getLogger(__name__)


class FoodItemCorrectionRequest(TypedDict, total=False):
    """A raw correction entry as received from the client.

    canonical_food_id is a string identifier that the use case resolves
    into a CanonicalFood entity before passing it to the domain.
    """

    food_item_id: str
    canonical_food_id: str
    estimated_weight_g: float
    ingredients: list[str]


class UpdateMealUseCase:
    """Applies user corrections to a meal draft.

    Corrections override AI predictions (business rule 6). Nutrition is
    recalculated from the corrected meal (business rule 7).
    """

    def __init__(
        self,
        meal_repository: MealRepository,
        nutrition_resolver: NutritionResolver,
        catalog: CanonicalFoodCatalog,
    ) -> None:
        self._meal_repository = meal_repository
        self._nutrition_resolver = nutrition_resolver
        self._catalog = catalog

    def execute(
        self,
        meal_id: str,
        corrections: list[FoodItemCorrectionRequest],
        name: str | None = None,
    ) -> Meal:
        """Apply corrections to a meal.

        Args:
            meal_id: The meal to correct.
            corrections: Raw correction entries with string food IDs.
            name: When given, renames the meal (empty clears the name).

        Returns:
            The corrected meal with recalculated nutrition.

        Raises:
            MealNotFoundError: If the meal does not exist.
            FoodNotFoundError: If a referenced canonical food is unknown.
        """
        meal = self._meal_repository.get_by_id(meal_id)
        if meal is None:
            raise MealNotFoundError(f"Meal '{meal_id}' not found")

        if corrections:
            domain_corrections = self._translate_corrections(corrections)
            meal.apply_corrections(domain_corrections)
            self._re_resolve_nutrition(meal)
            meal.recalculate_nutrition()
        if name is not None:
            # Renaming is metadata: it must not touch the meal state or
            # the nutrition, so it stays outside the corrections branch.
            meal.rename(name)
        self._meal_repository.save(meal)
        logger.info("Meal %s updated", meal_id)
        return meal

    def _translate_corrections(
        self,
        corrections: list[FoodItemCorrectionRequest],
    ) -> list[FoodItemCorrection]:
        """Resolve string food identifiers into CanonicalFood entities."""
        translated: list[FoodItemCorrection] = []
        for request in corrections:
            correction: FoodItemCorrection = {
                "food_item_id": request["food_item_id"],
            }
            if "canonical_food_id" in request:
                correction["canonical_food"] = self._resolve_food(
                    request["canonical_food_id"]
                )
            if "estimated_weight_g" in request:
                correction["estimated_weight_g"] = request[
                    "estimated_weight_g"
                ]
            if "ingredients" in request:
                correction["ingredients"] = request["ingredients"]
            translated.append(correction)
        return translated

    def _resolve_food(self, canonical_food_id: str) -> CanonicalFood:
        food = self._catalog.get_by_id(canonical_food_id)
        if food is None:
            raise FoodNotFoundError(
                f"Canonical food '{canonical_food_id}' not found"
            )
        return food

    def _re_resolve_nutrition(self, meal: Meal) -> None:
        """Refresh nutrition profiles for every corrected food item."""
        for item in meal.food_items:
            if item.is_corrected():
                self._resolve_item_nutrition(item)

    def _resolve_item_nutrition(self, item: FoodItem) -> None:
        if item.canonical_food is None:
            raise ValueError(
                f"Food item '{item.food_item_id}' has no canonical food"
            )
        item.set_nutrition_profile(
            self._nutrition_resolver.resolve(
                item.canonical_food,
                item.measurement,
            )
        )
