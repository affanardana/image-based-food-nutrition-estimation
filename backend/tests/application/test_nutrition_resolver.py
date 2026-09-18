"""Tests for NutritionResolver service."""

import pytest

from app.application.services.nutrition_resolver import NutritionResolver
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.measurement import Measurement
from app.domain.exceptions import NutritionUnavailableError
from app.domain.values.measurement_values import Weight
from app.domain.values.nutrition_values import NutritionProfile
from tests.application.fakes import FakeNutritionProvider

BURGER = CanonicalFood(id="burger", name="Burger", typical_weight_g=200.0)
PER_100G = NutritionProfile(
    calories_kcal=250.0,
    protein_g=12.0,
    fat_g=14.0,
    carbohydrates_g=20.0,
)


class TestNutritionResolver:
    def test_scales_to_measured_weight(self) -> None:
        provider = FakeNutritionProvider({"burger": PER_100G})
        resolver = NutritionResolver(provider)
        measurement = Measurement(weight=Weight(value_g=150.0))

        profile = resolver.resolve(BURGER, measurement)

        assert profile.calories_kcal == 375.0  # 250 * 1.5
        assert profile.protein_g == 18.0

    def test_falls_back_to_typical_weight(self) -> None:
        provider = FakeNutritionProvider({"burger": PER_100G})
        resolver = NutritionResolver(provider)
        measurement = Measurement()  # no weight measured

        profile = resolver.resolve(BURGER, measurement)

        assert profile.calories_kcal == 500.0  # 250 * 2.0 (200g typical)

    def test_unknown_food_raises(self) -> None:
        provider = FakeNutritionProvider({})
        resolver = NutritionResolver(provider)
        measurement = Measurement(weight=Weight(value_g=100.0))

        with pytest.raises(NutritionUnavailableError):
            resolver.resolve(BURGER, measurement)
