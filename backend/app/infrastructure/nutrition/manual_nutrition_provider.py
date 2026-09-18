"""ManualNutritionProvider — nutrition data from a local YAML database."""

from pathlib import Path
from typing import Any

import yaml

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.exceptions import NutritionUnavailableError
from app.domain.interfaces.nutrition_provider import NutritionProvider
from app.domain.values.nutrition_values import NutritionProfile


class ManualNutritionProvider(NutritionProvider):
    """A nutrition provider backed by a manually curated YAML database.

    The database contains per-100g nutrition values keyed by canonical
    food id. Useful for development, testing, and demos until a real
    source (Panganku, USDA) is integrated.
    """

    def __init__(self, database_path: str) -> None:
        raw = yaml.safe_load(Path(database_path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                f"Invalid nutrition database '{database_path}': "
                "expected a mapping"
            )
        foods_raw = raw.get("foods")
        if not isinstance(foods_raw, dict):
            raise ValueError(
                f"Invalid nutrition database '{database_path}': "
                "missing 'foods' mapping"
            )
        self._profiles = self._parse(foods_raw)

    @staticmethod
    def _parse(foods_raw: dict[str, Any]) -> dict[str, NutritionProfile]:
        profiles: dict[str, NutritionProfile] = {}
        for food_id, spec in foods_raw.items():
            if not isinstance(spec, dict):
                raise ValueError(
                    f"Invalid nutrition entry '{food_id}': expected a mapping"
                )
            profiles[food_id] = NutritionProfile(
                calories_kcal=float(spec["calories_kcal"]),
                protein_g=float(spec["protein_g"]),
                fat_g=float(spec["fat_g"]),
                carbohydrates_g=float(spec["carbohydrates_g"]),
                fiber_g=float(spec.get("fiber_g", 0.0)),
                sodium_mg=float(spec.get("sodium_mg", 0.0)),
            )
        return profiles

    def get_nutrition_per_100g(
        self,
        canonical_food: CanonicalFood,
    ) -> NutritionProfile:
        profile = self._profiles.get(canonical_food.id)
        if profile is None:
            raise NutritionUnavailableError(
                f"No nutrition data for '{canonical_food.id}' "
                f"in manual database"
            )
        return profile

    @property
    def provider_name(self) -> str:
        return "manual"
