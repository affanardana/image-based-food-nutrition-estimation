"""Tests for UpdateMealUseCase — correction workflow and recalculation."""

import pytest

from app.application.services.nutrition_resolver import NutritionResolver
from app.application.use_cases.update_meal import UpdateMealUseCase
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.food_item import CorrectionState, FoodItem
from app.domain.entities.meal import Meal, MealState
from app.domain.entities.measurement import Measurement
from app.domain.exceptions import MealNotFoundError
from app.domain.values.measurement_values import Weight
from app.domain.values.nutrition_values import NutritionProfile
from tests.application.fakes import (
    FakeCatalog,
    FakeMealRepository,
    FakeNutritionProvider,
)

PER_100G = NutritionProfile(calories_kcal=200.0, protein_g=10.0)


def make_draft_meal(meal_id: str = "meal_001") -> Meal:
    """Create a persisted draft meal with one 200g rice food item."""
    food = FoodItem(
        food_item_id="food_001",
        canonical_food=CanonicalFood(id="rice", name="Rice"),
        measurement=Measurement(weight=Weight(value_g=200.0)),
    )
    food.set_nutrition_profile(NutritionProfile(calories_kcal=400.0))
    meal = Meal(meal_id=meal_id, image_path="/storage/img.jpg")
    meal.add_food_item(food)
    meal.mark_draft()
    return meal


def make_catalog() -> FakeCatalog:
    """Build a catalog with rice and burger foods."""
    foods = [
        CanonicalFood(id="rice", name="Rice"),
        CanonicalFood(id="burger", name="Burger", typical_weight_g=200.0),
    ]
    return FakeCatalog(foods=foods, vision_mapping={})


def build_use_case(
    repo: FakeMealRepository,
    profiles: dict[str, NutritionProfile],
) -> UpdateMealUseCase:
    """Assemble an UpdateMealUseCase with fakes."""
    return UpdateMealUseCase(
        meal_repository=repo,
        nutrition_resolver=NutritionResolver(
            FakeNutritionProvider(profiles)
        ),
        catalog=make_catalog(),
    )


class TestUpdateMealUseCase:
    def test_corrections_override_and_recalculate(self) -> None:
        repo = FakeMealRepository()
        repo.save(make_draft_meal())
        use_case = build_use_case(repo, {"rice": PER_100G})

        updated = use_case.execute(
            "meal_001",
            [{"food_item_id": "food_001", "estimated_weight_g": 300.0}],
        )

        assert updated.state == MealState.CORRECTED
        item = updated.get_food_item("food_001")
        assert item.measurement.weight is not None
        assert item.measurement.weight.value_g == 300.0
        # Re-resolved: 200 kcal/100g × 3.0 (300g)
        assert item.nutrition_profile.calories_kcal == 600.0
        assert updated.nutrition_summary.total_calories_kcal == 600.0

    def test_correction_persisted(self) -> None:
        repo = FakeMealRepository()
        repo.save(make_draft_meal())
        use_case = build_use_case(repo, {"rice": PER_100G})

        use_case.execute(
            "meal_001",
            [{"food_item_id": "food_001", "estimated_weight_g": 300.0}],
        )

        stored = repo.get_by_id("meal_001")
        assert stored is not None
        assert stored.state == MealState.CORRECTED

    def test_unknown_meal_raises(self) -> None:
        use_case = build_use_case(FakeMealRepository(), {"rice": PER_100G})

        with pytest.raises(MealNotFoundError):
            use_case.execute("missing_meal", [])

    def test_canonical_food_change_is_re_resolved(self) -> None:
        repo = FakeMealRepository()
        repo.save(make_draft_meal())
        use_case = build_use_case(
            repo,
            {"burger": NutritionProfile(calories_kcal=250.0)},
        )

        updated = use_case.execute(
            "meal_001",
            [{"food_item_id": "food_001", "canonical_food_id": "burger"}],
        )

        item = updated.get_food_item("food_001")
        assert item.correction_state == CorrectionState.USER_CORRECTED
        assert item.canonical_food is not None
        assert item.canonical_food.id == "burger"
        # Burger nutrition resolved for the same 200g measurement
        assert item.nutrition_profile.calories_kcal == 500.0
