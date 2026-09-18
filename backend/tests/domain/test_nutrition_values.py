"""Tests for NutritionValue and NutritionProfile value objects."""

import pytest

from app.domain.values.nutrition_values import NutritionProfile, NutritionValue


class TestNutritionValue:
    def test_valid_value(self) -> None:
        nv = NutritionValue(value=100.0, unit="kcal")
        assert nv.value == 100.0
        assert nv.unit == "kcal"

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            NutritionValue(value=-10.0, unit="g")

    def test_str_format(self) -> None:
        nv = NutritionValue(value=10.5, unit="g")
        assert "10.5 g" in str(nv)


class TestNutritionProfile:
    def test_default_empty(self) -> None:
        p = NutritionProfile()
        assert p.empty
        assert p.calories_kcal == 0.0

    def test_valid_profile(self) -> None:
        p = NutritionProfile(
            calories_kcal=510.0,
            protein_g=22.3,
            fat_g=28.6,
            carbohydrates_g=39.7,
            fiber_g=2.0,
            sodium_mg=850.0,
        )
        assert not p.empty

    def test_negative_field_raises(self) -> None:
        with pytest.raises(ValueError, match="protein_g must be non-negative"):
            NutritionProfile(protein_g=-1.0)

    def test_scale(self) -> None:
        p = NutritionProfile(calories_kcal=100.0, protein_g=10.0)
        scaled = p.scale(2.0)
        assert scaled.calories_kcal == 200.0
        assert scaled.protein_g == 20.0

    def test_scale_preserves_original(self) -> None:
        p = NutritionProfile(calories_kcal=100.0)
        p.scale(2.0)
        assert p.calories_kcal == 100.0  # immutable

    def test_scale_negative_factor_raises(self) -> None:
        p = NutritionProfile(calories_kcal=100.0)
        with pytest.raises(ValueError, match="non-negative"):
            p.scale(-1.0)

    def test_add_profiles(self) -> None:
        a = NutritionProfile(calories_kcal=300.0, protein_g=15.0)
        b = NutritionProfile(calories_kcal=200.0, protein_g=10.0)
        combined = a + b
        assert combined.calories_kcal == 500.0
        assert combined.protein_g == 25.0
