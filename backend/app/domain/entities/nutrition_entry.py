"""NutritionEntry entity — one nutrition record from a NutritionSource."""

from dataclasses import dataclass

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.nutrition_source import NutritionSource
from app.domain.values.nutrition_values import NutritionProfile


@dataclass(frozen=True)
class NutritionEntry:
    """A nutrition record retrieved from a NutritionSource for a specific CanonicalFood.

    Multiple NutritionEntries may correspond to the same CanonicalFood
    (e.g., from different databases).
    """

    source: NutritionSource
    canonical_food: CanonicalFood
    profile: NutritionProfile

    def __str__(self) -> str:
        return f"{self.canonical_food.name} — {self.source.name}"
