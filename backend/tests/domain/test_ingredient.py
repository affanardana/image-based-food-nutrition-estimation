"""Tests for Ingredient entity."""

from app.domain.entities.ingredient import Ingredient, IngredientSource


class TestIngredient:
    def test_create_predicted(self) -> None:
        ing = Ingredient(name="Bun")
        assert ing.name == "Bun"
        assert ing.source == IngredientSource.PREDICTED

    def test_create_manual(self) -> None:
        ing = Ingredient(name="Cheese", source=IngredientSource.MANUAL)
        assert ing.source == IngredientSource.MANUAL

    def test_str(self) -> None:
        ing = Ingredient(name="Lettuce")
        assert str(ing) == "Lettuce"

    def test_equality(self) -> None:
        assert Ingredient(name="Tomato") == Ingredient(name="Tomato")
