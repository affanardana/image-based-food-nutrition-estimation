"""Tests for FoodItem entity and its correction operations."""

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.food_item import CorrectionState, FoodItem
from app.domain.entities.ingredient import Ingredient, IngredientSource
from app.domain.values.measurement_values import Weight
from app.domain.values.nutrition_values import NutritionProfile
from tests.helpers import make_segment


class TestFoodItem:
    def test_create_default(self) -> None:
        fi = FoodItem(food_item_id="food_001")
        assert fi.food_item_id == "food_001"
        assert fi.correction_state == CorrectionState.LABELED
        assert fi.ingredients == []
        assert fi.segments == []
        assert fi.nutrition_profile.empty

    def test_create_with_segments(self) -> None:
        segments = [make_segment("seg_001"), make_segment("seg_002")]
        fi = FoodItem(
            food_item_id="food_001",
            canonical_food=CanonicalFood(id="sate", name="Sate"),
            segments=segments,
        )
        assert fi.segments == segments
        assert len(fi.segments) == 2

    def test_change_canonical_food(self) -> None:
        fi = FoodItem(food_item_id="food_001")
        fi.change_canonical_food(CanonicalFood(id="burger", name="Burger"))
        assert fi.canonical_food == CanonicalFood(id="burger", name="Burger")
        assert fi.correction_state == CorrectionState.USER_CORRECTED
        assert len(fi.corrections) == 1
        assert fi.corrections[0].field == "canonical_food"

    def test_update_weight(self) -> None:
        fi = FoodItem(food_item_id="food_001")
        fi.update_weight(Weight(value_g=210.0))
        assert fi.measurement.weight.value_g == 210.0  # type: ignore[union-attr]
        assert fi.correction_state == CorrectionState.USER_CORRECTED

    def test_replace_ingredients(self) -> None:
        fi = FoodItem(food_item_id="food_001")
        fi.ingredients = [
            Ingredient(name="Bun", source=IngredientSource.PREDICTED)
        ]
        fi.replace_ingredients(["Bun", "Beef Patty", "Cheese"])
        assert len(fi.ingredients) == 3
        assert all(i.source == IngredientSource.MANUAL for i in fi.ingredients)
        assert fi.correction_state == CorrectionState.USER_CORRECTED

    def test_set_nutrition_profile(self) -> None:
        fi = FoodItem(food_item_id="food_001")
        profile = NutritionProfile(calories_kcal=510.0)
        fi.set_nutrition_profile(profile)
        assert fi.nutrition_profile.calories_kcal == 510.0

    def test_is_corrected(self) -> None:
        fi = FoodItem(food_item_id="food_001")
        assert not fi.is_corrected()
        fi.change_canonical_food(CanonicalFood(id="burger", name="Burger"))
        assert fi.is_corrected()
