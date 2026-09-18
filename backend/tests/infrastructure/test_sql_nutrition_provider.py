"""Tests for SqlNutritionProvider — SQLite-backed, no server needed."""

import pytest
from sqlalchemy import Engine, insert

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.exceptions import NutritionUnavailableError
from app.infrastructure.nutrition.sql_nutrition_provider import (
    DEFAULT_SOURCE,
    SqlNutritionProvider,
)
from app.infrastructure.persistence.schema import (
    canonical_foods,
    nutrition_entries,
)
from tests.infrastructure.helpers import make_sqlite_engine

SATE = CanonicalFood(id="sate", name="Sate")

CSV_ENTRY = {
    "canonical_food_id": "sate",
    "source": "nutrition_csv",
    "calories_kcal": 200.0,
    "protein_g": 20.0,
    "fat_g": 10.0,
    "carbohydrates_g": 5.0,
    "fiber_g": 1.0,
    "sodium_mg": 400.0,
}

CURATED_ENTRY = {
    "canonical_food_id": "sate",
    "source": "manual",
    "calories_kcal": 218.0,
    "protein_g": 24.5,
    "fat_g": 11.2,
    "carbohydrates_g": 4.8,
    "fiber_g": 0.0,
    "sodium_mg": 480.0,
}


def make_engine(entries: list[dict[str, object]]) -> Engine:
    """An engine holding one canonical food and the given entries."""
    engine = make_sqlite_engine()
    with engine.begin() as connection:
        connection.execute(
            insert(canonical_foods),
            [
                {
                    "id": "sate",
                    "name": "Sate",
                    "image_url": None,
                    "typical_weight_g": 100.0,
                    "density_g_per_cm3": None,
                    "calibration_factor": None,
                }
            ],
        )
        if entries:
            connection.execute(insert(nutrition_entries), entries)
    return engine


class TestGetNutritionPer100g:
    def test_returns_profile_from_the_preferred_source(self) -> None:
        engine = make_engine([CSV_ENTRY, CURATED_ENTRY])
        provider = SqlNutritionProvider(engine, source=DEFAULT_SOURCE)

        profile = provider.get_nutrition_per_100g(SATE)

        assert profile.calories_kcal == 200.0
        assert profile.sodium_mg == 400.0

    def test_falls_back_to_another_source(self) -> None:
        engine = make_engine([CURATED_ENTRY])
        provider = SqlNutritionProvider(engine, source="nutrition_csv")

        profile = provider.get_nutrition_per_100g(SATE)

        assert profile.calories_kcal == 218.0

    def test_unknown_food_raises(self) -> None:
        engine = make_engine([CSV_ENTRY])
        provider = SqlNutritionProvider(engine)

        with pytest.raises(NutritionUnavailableError):
            provider.get_nutrition_per_100g(
                CanonicalFood(id="missing", name="Missing")
            )

    def test_provider_metadata(self) -> None:
        engine = make_engine([CSV_ENTRY])
        provider = SqlNutritionProvider(engine, source="manual")

        assert provider.provider_name == "sql"
        assert provider.source == "manual"
