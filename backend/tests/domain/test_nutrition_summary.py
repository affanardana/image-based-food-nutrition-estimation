"""Tests for NutritionSummary entity."""

from app.domain.entities.nutrition_summary import NutritionSummary
from app.domain.values.nutrition_values import NutritionProfile


class TestNutritionSummary:
    def test_empty_summary(self) -> None:
        ns = NutritionSummary()
        assert ns.total_calories_kcal == 0.0
        assert ns.total_protein_g == 0.0

    def test_recalculate_from_profiles(self) -> None:
        profiles = [
            NutritionProfile(calories_kcal=300.0, protein_g=15.0, fat_g=12.0),
            NutritionProfile(calories_kcal=200.0, protein_g=10.0, fat_g=8.0),
        ]
        ns = NutritionSummary()
        ns.recalculate(profiles)
        assert ns.total_calories_kcal == 500.0
        assert ns.total_protein_g == 25.0
        assert ns.total_fat_g == 20.0

    def test_from_profiles_classmethod(self) -> None:
        profiles = [
            NutritionProfile(calories_kcal=100.0),
            NutritionProfile(calories_kcal=200.0),
        ]
        ns = NutritionSummary.from_profiles(profiles)
        assert ns.total_calories_kcal == 300.0

    def test_recalculate_overwrites_previous(self) -> None:
        profiles = [NutritionProfile(calories_kcal=500.0)]
        ns = NutritionSummary.from_profiles(profiles)
        ns.recalculate([NutritionProfile(calories_kcal=100.0)])
        assert ns.total_calories_kcal == 100.0
