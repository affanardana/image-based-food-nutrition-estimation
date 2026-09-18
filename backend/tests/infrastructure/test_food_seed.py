"""Tests for food seed construction and loading."""

from pathlib import Path

from app.infrastructure.catalog.sql_canonical_food_catalog import (
    SqlCanonicalFoodCatalog,
)
from app.infrastructure.nutrition.sql_nutrition_provider import (
    SqlNutritionProvider,
)
from app.infrastructure.persistence.food_seed import (
    apply_seed_data,
    build_seed_data,
    slugify,
)
from tests.infrastructure.helpers import make_sqlite_engine

CSV_ROWS = """id,calories,proteins,fat,carbohydrate,name,image
13,110,2,0.5,25,Sate,https://img.test/sate.jpg
1,280,9.2,28.4,0,Abon,https://img.test/abon.jpg
7,513,23.7,37,21.3,Abon,https://img.test/abon-2.jpg
"""

MAPPINGS_YAML = """
canonical_foods:
  sate:
    name: "Sate"
    typical_weight_g: 100.0
    physical_properties:
      density_g_per_cm3: 0.95
      calibration_factor: 15.0
    vision_labels:
      - "sate"
      - "satay"
  lontong:
    name: "Lontong"
    typical_weight_g: 100.0
    physical_properties:
      density_g_per_cm3: 0.85
      calibration_factor: 25.0
    vision_labels:
      - "lontong"
"""

CURATED_NUTRITION_YAML = """
foods:
  sate:
    calories_kcal: 218.0
    protein_g: 24.5
    fat_g: 11.2
    carbohydrates_g: 4.8
  lontong:
    calories_kcal: 130.0
    protein_g: 2.2
    fat_g: 0.4
    carbohydrates_g: 28.5
"""


def write_sources(tmp_path: Path) -> tuple[str, str, str]:
    """Write the fixture sources and return their paths."""
    csv_path = tmp_path / "nutrition.csv"
    csv_path.write_text(CSV_ROWS, encoding="utf-8")
    mappings_path = tmp_path / "canonical_foods.yaml"
    mappings_path.write_text(MAPPINGS_YAML, encoding="utf-8")
    curated_path = tmp_path / "nutrition_database.yaml"
    curated_path.write_text(CURATED_NUTRITION_YAML, encoding="utf-8")
    return str(csv_path), str(mappings_path), str(curated_path)


class TestSlugify:
    def test_lowercases_and_joins_words(self) -> None:
        assert slugify("Nasi Goreng ") == "nasi_goreng"

    def test_strips_punctuation(self) -> None:
        assert slugify("Akar tonjong segar") == "akar_tonjong_segar"

    def test_empty_name_falls_back(self) -> None:
        assert slugify("  ") == "food"


class TestBuildSeedData:
    def test_every_csv_row_becomes_a_food(self, tmp_path: Path) -> None:
        data = build_seed_data(*write_sources(tmp_path))

        ids = sorted(food.id for food in data.foods)
        assert ids == ["abon", "abon_7", "lontong", "sate"]

    def test_duplicate_names_get_distinct_slugs(self, tmp_path: Path) -> None:
        data = build_seed_data(*write_sources(tmp_path))

        # The second "Abon" (source id 7) is disambiguated
        assert any(food.id == "abon_7" for food in data.foods)

    def test_curated_properties_merge_into_csv_food(
        self,
        tmp_path: Path,
    ) -> None:
        data = build_seed_data(*write_sources(tmp_path))

        sate = next(food for food in data.foods if food.id == "sate")
        assert sate.typical_weight_g == 100.0
        assert sate.density_g_per_cm3 == 0.95
        assert sate.calibration_factor == 15.0
        assert sate.image_url == "https://img.test/sate.jpg"

    def test_curated_food_absent_from_csv_keeps_curated_nutrition(
        self,
        tmp_path: Path,
    ) -> None:
        data = build_seed_data(*write_sources(tmp_path))

        entries = [
            entry
            for entry in data.nutrition
            if entry.canonical_food_id == "lontong"
        ]
        assert len(entries) == 1
        assert entries[0].source == "manual"
        assert entries[0].calories_kcal == 130.0

    def test_csv_nutrition_wins_for_merged_food(self, tmp_path: Path) -> None:
        data = build_seed_data(*write_sources(tmp_path))

        entries = [
            entry
            for entry in data.nutrition
            if entry.canonical_food_id == "sate"
        ]
        assert len(entries) == 1
        assert entries[0].source == "nutrition_csv"
        assert entries[0].calories_kcal == 110.0

    def test_vision_labels_collected(self, tmp_path: Path) -> None:
        data = build_seed_data(*write_sources(tmp_path))

        labels = {label.label: label.canonical_food_id for label in data.vision_labels}
        assert labels == {
            "sate": "sate",
            "satay": "sate",
            "lontong": "lontong",
        }


class TestApplySeedData:
    def test_seeded_database_serves_catalog_and_nutrition(
        self,
        tmp_path: Path,
    ) -> None:
        data = build_seed_data(*write_sources(tmp_path))
        engine = make_sqlite_engine()

        apply_seed_data(engine, data)

        catalog = SqlCanonicalFoodCatalog(engine)
        provider = SqlNutritionProvider(engine, source="nutrition_csv")
        sate = catalog.get_by_id("sate")
        assert sate is not None
        assert sate.physical_properties.density_g_per_cm3 == 0.95
        # CSV entry preferred, curated entry available as fallback
        assert provider.get_nutrition_per_100g(sate).calories_kcal == 110.0
        lontong = catalog.get_by_id("lontong")
        assert lontong is not None
        assert provider.get_nutrition_per_100g(lontong).calories_kcal == 130.0
        # Only the curated foods carry vision labels, ordered by name
        assert [food.id for food in catalog.list_detectable_foods()] == [
            "lontong",
            "sate",
        ]

    def test_reseeding_is_idempotent(self, tmp_path: Path) -> None:
        data = build_seed_data(*write_sources(tmp_path))
        engine = make_sqlite_engine()

        apply_seed_data(engine, data)
        apply_seed_data(engine, data)

        catalog = SqlCanonicalFoodCatalog(engine)
        assert len(catalog.search("", limit=100)) == len(data.foods)
