"""Tests for SqlCanonicalFoodCatalog — SQLite-backed, no server needed."""

import pytest
from sqlalchemy import Engine, insert

from app.domain.entities.vision_class import VisionClass
from app.infrastructure.catalog.sql_canonical_food_catalog import (
    SqlCanonicalFoodCatalog,
)
from app.infrastructure.persistence.schema import (
    canonical_foods,
    vision_labels,
)
from tests.infrastructure.helpers import make_sqlite_engine


@pytest.fixture
def engine() -> Engine:
    """A catalog holding two foods, one of them detectable."""
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
                    "density_g_per_cm3": 0.95,
                    "calibration_factor": 15.0,
                },
                {
                    "id": "abon",
                    "name": "Abon",
                    "image_url": "https://img.test/abon.jpg",
                    "typical_weight_g": 150.0,
                    "density_g_per_cm3": None,
                    "calibration_factor": None,
                },
            ],
        )
        connection.execute(
            insert(vision_labels),
            [
                {"label": "sate", "canonical_food_id": "sate"},
                {"label": "satay", "canonical_food_id": "sate"},
            ],
        )
    return engine


class TestGetById:
    def test_returns_food_with_physical_properties(self, engine: Engine) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        food = catalog.get_by_id("sate")

        assert food is not None
        assert food.name == "Sate"
        assert food.typical_weight_g == 100.0
        assert food.physical_properties.density_g_per_cm3 == 0.95
        assert food.physical_properties.calibration_factor == 15.0

    def test_missing_food_returns_none(self, engine: Engine) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        assert catalog.get_by_id("missing") is None


class TestMapFromVisionClass:
    def test_maps_known_label(self, engine: Engine) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        food = catalog.map_from_vision_class(VisionClass(label="satay"))

        assert food is not None
        assert food.id == "sate"

    def test_unknown_label_returns_none(self, engine: Engine) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        assert catalog.map_from_vision_class(VisionClass(label="nope")) is None


class TestSearch:
    def test_empty_query_returns_all_ordered_by_name(
        self,
        engine: Engine,
    ) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        results = catalog.search("")

        assert [food.id for food in results] == ["abon", "sate"]

    def test_matches_name_case_insensitively(self, engine: Engine) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        results = catalog.search("SAT")

        assert [food.id for food in results] == ["sate"]

    def test_respects_limit(self, engine: Engine) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        assert len(catalog.search("", limit=1)) == 1


class TestSearchRelevance:
    def test_prefix_matches_rank_first(self) -> None:
        engine = make_sqlite_engine()
        with engine.begin() as connection:
            connection.execute(
                insert(canonical_foods),
                [
                    {
                        "id": "rice",
                        "name": "Rice",
                        "image_url": None,
                        "typical_weight_g": 200.0,
                        "density_g_per_cm3": None,
                        "calibration_factor": None,
                    },
                    {
                        "id": "keripik",
                        "name": "Keripik",
                        "image_url": None,
                        "typical_weight_g": 100.0,
                        "density_g_per_cm3": None,
                        "calibration_factor": None,
                    },
                ],
            )
        catalog = SqlCanonicalFoodCatalog(engine)

        results = catalog.search("ri")

        # "Rice" starts with the keyword; "Keripik" only contains it
        assert [food.id for food in results] == ["rice", "keripik"]

    def test_non_prefix_matches_are_still_returned(self) -> None:
        engine = make_sqlite_engine()
        with engine.begin() as connection:
            connection.execute(
                insert(canonical_foods),
                [
                    {
                        "id": "keripik",
                        "name": "Keripik",
                        "image_url": None,
                        "typical_weight_g": 100.0,
                        "density_g_per_cm3": None,
                        "calibration_factor": None,
                    }
                ],
            )
        catalog = SqlCanonicalFoodCatalog(engine)

        assert [food.id for food in catalog.search("rip")] == ["keripik"]


class TestListDetectableFoods:
    def test_returns_only_foods_with_vision_labels(self, engine: Engine) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        results = catalog.list_detectable_foods()

        assert [food.id for food in results] == ["sate"]

    def test_does_not_duplicate_foods_with_several_labels(
        self,
        engine: Engine,
    ) -> None:
        catalog = SqlCanonicalFoodCatalog(engine)

        # sate has two vision labels but must appear once
        assert len(catalog.list_detectable_foods()) == 1
