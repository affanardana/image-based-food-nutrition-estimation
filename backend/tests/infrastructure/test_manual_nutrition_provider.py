"""Tests for ManualNutritionProvider."""

from pathlib import Path

import pytest

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.exceptions import NutritionUnavailableError
from app.infrastructure.nutrition.manual_nutrition_provider import (
    ManualNutritionProvider,
)

DATABASE_PATH = str(
    Path(__file__).resolve().parents[2] / "data" / "nutrition_database.yaml"
)


def make_provider() -> ManualNutritionProvider:
    return ManualNutritionProvider(DATABASE_PATH)


class TestManualNutritionProvider:
    def test_returns_per_100g_profile(self) -> None:
        provider = make_provider()

        profile = provider.get_nutrition_per_100g(
            CanonicalFood(id="sate", name="Sate")
        )

        assert profile.calories_kcal == 218.0
        assert profile.protein_g == 24.5
        assert profile.fat_g == 11.2
        assert profile.carbohydrates_g == 4.8

    def test_returns_lontong_profile(self) -> None:
        provider = make_provider()

        profile = provider.get_nutrition_per_100g(
            CanonicalFood(id="lontong", name="Lontong")
        )

        assert profile.calories_kcal == 130.0
        assert profile.carbohydrates_g == 28.5

    def test_unknown_food_raises(self) -> None:
        provider = make_provider()

        with pytest.raises(NutritionUnavailableError, match="bakso"):
            provider.get_nutrition_per_100g(
                CanonicalFood(id="bakso", name="Bakso")
            )

    def test_provider_name(self) -> None:
        assert make_provider().provider_name == "manual"
