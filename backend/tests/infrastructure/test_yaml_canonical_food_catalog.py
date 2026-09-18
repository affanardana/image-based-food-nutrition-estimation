"""Tests for YamlCanonicalFoodCatalog."""

from pathlib import Path

from app.domain.entities.vision_class import VisionClass
from app.infrastructure.catalog.yaml_canonical_food_catalog import (
    YamlCanonicalFoodCatalog,
)

CONFIG_PATH = str(
    Path(__file__).resolve().parents[2] / "mappings" / "canonical_foods.yaml"
)


def make_catalog() -> YamlCanonicalFoodCatalog:
    return YamlCanonicalFoodCatalog(CONFIG_PATH)


class TestYamlCanonicalFoodCatalog:
    def test_get_by_id_includes_physical_properties(self) -> None:
        catalog = make_catalog()

        sate = catalog.get_by_id("sate")

        assert sate is not None
        assert sate.name == "Sate"
        assert sate.typical_weight_g == 100.0
        assert sate.physical_properties.density_g_per_cm3 == 0.95
        assert sate.physical_properties.calibration_factor == 15.0

    def test_get_by_id_unknown_returns_none(self) -> None:
        catalog = make_catalog()

        assert catalog.get_by_id("unknown_food") is None

    def test_map_from_vision_class(self) -> None:
        catalog = make_catalog()

        food = catalog.map_from_vision_class(VisionClass(label="cheeseburger"))

        assert food is not None
        assert food.id == "burger"

    def test_map_unknown_label_returns_none(self) -> None:
        catalog = make_catalog()

        assert (
            catalog.map_from_vision_class(VisionClass(label="unknown")) is None
        )

    def test_multiple_labels_map_to_one_food(self) -> None:
        catalog = make_catalog()

        for label in ["sate", "satay", "chicken_satay"]:
            food = catalog.map_from_vision_class(VisionClass(label=label))
            assert food is not None
            assert food.id == "sate"

    def test_search_is_case_insensitive(self) -> None:
        catalog = make_catalog()

        results = catalog.search("SATE")

        assert [food.id for food in results] == ["sate"]

    def test_search_empty_query_returns_all(self) -> None:
        catalog = make_catalog()

        results = catalog.search("")

        assert len(results) == 12

    def test_prefix_matches_rank_first(self) -> None:
        catalog = make_catalog()

        results = catalog.search("ri")

        # "Rice" starts with the keyword. The others only contain it:
        # "fried_chicken" and "fried_rice" match through their ids, and
        # tie-break alphabetically by name ("Fried Chicken" before
        # "Nasi Goreng").
        assert [food.id for food in results] == [
            "rice",
            "fried_chicken",
            "fried_rice",
        ]

    def test_search_limit_respected(self) -> None:
        catalog = make_catalog()

        results = catalog.search("", limit=3)

        assert len(results) == 3

    def test_list_detectable_foods_returns_labelled_foods(self) -> None:
        catalog = make_catalog()

        detectable = catalog.list_detectable_foods()

        # Every curated food carries vision labels
        assert len(detectable) == 12
        assert detectable[0].name <= detectable[-1].name
        assert "sate" in [food.id for food in detectable]
