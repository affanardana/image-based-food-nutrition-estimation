"""Nutrition value objects — per-nutrient values and full nutrition profiles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NutritionValue:
    """A single nutritional quantity in grams or kcal.

    Raises:
        ValueError: If the value is negative.
    """

    value: float
    unit: str  # "g", "kcal", "mg", "mcg"

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError(f"NutritionValue must be non-negative, got {self.value}")

    def __str__(self) -> str:
        return f"{self.value:.1f} {self.unit}"


@dataclass(frozen=True)
class NutritionProfile:
    """Complete nutritional profile for a single food item.

    Represents the nutritional values per standard serving or estimated weight.
    """

    calories_kcal: float = 0.0
    protein_g: float = 0.0
    fat_g: float = 0.0
    carbohydrates_g: float = 0.0
    fiber_g: float = 0.0
    sodium_mg: float = 0.0

    def __post_init__(self) -> None:
        for field_name in [
            "calories_kcal",
            "protein_g",
            "fat_g",
            "carbohydrates_g",
            "fiber_g",
            "sodium_mg",
        ]:
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(
                    f"{field_name} must be non-negative, got {value}"
                )

    def scale(self, factor: float) -> "NutritionProfile":
        """Return a new profile scaled by the given factor.

        Used when adjusting nutrition based on actual vs. reference weight.
        """
        if factor < 0:
            raise ValueError(f"Scale factor must be non-negative, got {factor}")
        return NutritionProfile(
            calories_kcal=self.calories_kcal * factor,
            protein_g=self.protein_g * factor,
            fat_g=self.fat_g * factor,
            carbohydrates_g=self.carbohydrates_g * factor,
            fiber_g=self.fiber_g * factor,
            sodium_mg=self.sodium_mg * factor,
        )

    def __add__(self, other: "NutritionProfile") -> "NutritionProfile":
        """Combine two nutrition profiles (for meal aggregation)."""
        return NutritionProfile(
            calories_kcal=self.calories_kcal + other.calories_kcal,
            protein_g=self.protein_g + other.protein_g,
            fat_g=self.fat_g + other.fat_g,
            carbohydrates_g=self.carbohydrates_g + other.carbohydrates_g,
            fiber_g=self.fiber_g + other.fiber_g,
            sodium_mg=self.sodium_mg + other.sodium_mg,
        )

    @property
    def empty(self) -> bool:
        """Return True if all nutritional values are zero."""
        return all(
            v == 0.0
            for v in [
                self.calories_kcal,
                self.protein_g,
                self.fat_g,
                self.carbohydrates_g,
                self.fiber_g,
                self.sodium_mg,
            ]
        )
