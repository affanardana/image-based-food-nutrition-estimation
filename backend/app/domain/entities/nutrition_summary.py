"""NutritionSummary entity — aggregated nutrition for an entire meal."""

from dataclasses import dataclass

from app.domain.values.nutrition_values import NutritionProfile


@dataclass
class NutritionSummary:
    """Aggregated nutritional totals for an entire meal.

    Computed by summing all FoodItem nutrition profiles.
    """

    total_calories_kcal: float = 0.0
    total_protein_g: float = 0.0
    total_fat_g: float = 0.0
    total_carbohydrates_g: float = 0.0
    total_fiber_g: float = 0.0
    total_sodium_mg: float = 0.0

    def recalculate(self, profiles: list[NutritionProfile]) -> None:
        """Recalculate the summary from a list of nutrition profiles."""
        combined = NutritionProfile()
        for profile in profiles:
            combined = combined + profile
        self.total_calories_kcal = combined.calories_kcal
        self.total_protein_g = combined.protein_g
        self.total_fat_g = combined.fat_g
        self.total_carbohydrates_g = combined.carbohydrates_g
        self.total_fiber_g = combined.fiber_g
        self.total_sodium_mg = combined.sodium_mg

    @classmethod
    def from_profiles(cls, profiles: list[NutritionProfile]) -> "NutritionSummary":
        """Create a summary from a list of nutrition profiles."""
        summary = cls()
        summary.recalculate(profiles)
        return summary
