"""Seed data construction for the food database.

Two sources are merged into one dataset:

- ``data/nutrition.csv`` — the broad food database (Indonesian foods,
  per-100g nutrition). Every row becomes a canonical food.
- ``mappings/canonical_foods.yaml`` + ``data/nutrition_database.yaml`` —
  the curated, calibrated foods. These carry physical properties
  (density, calibration factor) and VisionClass mappings that the CSV
  does not; their nutrition is the curated reference data.

The same food may appear in both: the CSV supplies nutrition, the
curated files supply physical properties and vision labels.
"""

import csv
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Engine, delete, insert

from app.infrastructure.persistence.schema import (
    canonical_foods,
    metadata,
    nutrition_entries,
    vision_labels,
)

CSV_NUTRITION_SOURCE = "nutrition_csv"
CURATED_NUTRITION_SOURCE = "manual"
DEFAULT_TYPICAL_WEIGHT_G = 150.0


@dataclass(frozen=True)
class SeedFood:
    """A canonical food row."""

    id: str
    name: str
    image_url: str | None
    typical_weight_g: float
    density_g_per_cm3: float | None
    calibration_factor: float | None


@dataclass(frozen=True)
class SeedNutrition:
    """A per-100g nutrition row."""

    canonical_food_id: str
    source: str
    calories_kcal: float
    protein_g: float
    fat_g: float
    carbohydrates_g: float
    fiber_g: float
    sodium_mg: float


@dataclass(frozen=True)
class SeedVisionLabel:
    """A VisionClass → CanonicalFood mapping row."""

    label: str
    canonical_food_id: str


@dataclass(frozen=True)
class FoodSeedData:
    """Everything needed to populate the food database."""

    foods: list[SeedFood]
    nutrition: list[SeedNutrition]
    vision_labels: list[SeedVisionLabel]


def slugify(name: str) -> str:
    """Convert a food name into an identifier-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "food"


def build_seed_data(
    csv_path: str,
    mappings_path: str,
    curated_nutrition_path: str,
) -> FoodSeedData:
    """Build the seed dataset from the CSV and the curated YAML files."""
    foods: dict[str, SeedFood] = {}
    nutrition: list[SeedNutrition] = []

    _load_csv_foods(csv_path, foods, nutrition)
    _merge_curated_foods(
        mappings_path,
        curated_nutrition_path,
        foods,
        nutrition,
    )
    return FoodSeedData(
        foods=list(foods.values()),
        nutrition=nutrition,
        vision_labels=_load_vision_labels(mappings_path),
    )


def apply_seed_data(engine: Engine, data: FoodSeedData) -> None:
    """Create the schema and replace all food data (full refresh).

    Existing rows are removed first, so re-seeding discards any manual
    calibration made directly in the database.
    """
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(delete(vision_labels))
        connection.execute(delete(nutrition_entries))
        connection.execute(delete(canonical_foods))
        if data.foods:
            connection.execute(
                insert(canonical_foods),
                [asdict(food) for food in data.foods],
            )
        if data.nutrition:
            connection.execute(
                insert(nutrition_entries),
                [asdict(entry) for entry in data.nutrition],
            )
        if data.vision_labels:
            connection.execute(
                insert(vision_labels),
                [asdict(label) for label in data.vision_labels],
            )


def _load_csv_foods(
    csv_path: str,
    foods: dict[str, SeedFood],
    nutrition: list[SeedNutrition],
) -> None:
    """Turn every CSV row into a canonical food with nutrition."""
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("name") or "").strip()
            if not name:
                continue
            food_id = _unique_slug(name, row.get("id", ""), foods)
            foods[food_id] = SeedFood(
                id=food_id,
                name=name,
                image_url=(row.get("image") or "").strip() or None,
                typical_weight_g=DEFAULT_TYPICAL_WEIGHT_G,
                density_g_per_cm3=None,
                calibration_factor=None,
            )
            nutrition.append(
                SeedNutrition(
                    canonical_food_id=food_id,
                    source=CSV_NUTRITION_SOURCE,
                    calories_kcal=_to_float(row.get("calories"), name),
                    protein_g=_to_float(row.get("proteins"), name),
                    fat_g=_to_float(row.get("fat"), name),
                    carbohydrates_g=_to_float(row.get("carbohydrate"), name),
                    fiber_g=0.0,
                    sodium_mg=0.0,
                )
            )


def _merge_curated_foods(
    mappings_path: str,
    curated_nutrition_path: str,
    foods: dict[str, SeedFood],
    nutrition: list[SeedNutrition],
) -> None:
    """Merge calibrated foods, adding physical properties and labels."""
    curated = _load_yaml(mappings_path).get("canonical_foods") or {}
    curated_nutrition = _load_yaml(curated_nutrition_path).get("foods") or {}

    for food_id, spec in curated.items():
        properties = spec.get("physical_properties") or {}
        typical_weight_g = float(
            spec.get("typical_weight_g", DEFAULT_TYPICAL_WEIGHT_G)
        )
        density = properties.get("density_g_per_cm3")
        calibration = properties.get("calibration_factor")

        existing = foods.get(food_id)
        if existing is not None:
            # The CSV supplied nutrition; the curated file supplies the
            # physical properties that portion estimation needs.
            foods[food_id] = replace(
                existing,
                typical_weight_g=typical_weight_g,
                density_g_per_cm3=density,
                calibration_factor=calibration,
            )
            continue

        foods[food_id] = SeedFood(
            id=food_id,
            name=spec["name"],
            image_url=None,
            typical_weight_g=typical_weight_g,
            density_g_per_cm3=density,
            calibration_factor=calibration,
        )
        entry = curated_nutrition.get(food_id)
        if entry is not None:
            nutrition.append(
                SeedNutrition(
                    canonical_food_id=food_id,
                    source=CURATED_NUTRITION_SOURCE,
                    calories_kcal=float(entry["calories_kcal"]),
                    protein_g=float(entry["protein_g"]),
                    fat_g=float(entry["fat_g"]),
                    carbohydrates_g=float(entry["carbohydrates_g"]),
                    fiber_g=float(entry.get("fiber_g", 0.0)),
                    sodium_mg=float(entry.get("sodium_mg", 0.0)),
                )
            )


def _load_vision_labels(mappings_path: str) -> list[SeedVisionLabel]:
    """Collect every VisionClass mapping from the curated file."""
    curated = _load_yaml(mappings_path).get("canonical_foods") or {}
    labels: list[SeedVisionLabel] = []
    for food_id, spec in curated.items():
        for label in spec.get("vision_labels", []):
            labels.append(
                SeedVisionLabel(label=label, canonical_food_id=food_id)
            )
    return labels


def _load_yaml(path: str) -> dict[str, Any]:
    """Read a YAML file into a mapping."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid YAML configuration '{path}': expected a mapping")
    return raw


def _unique_slug(
    name: str,
    raw_id: str,
    taken: dict[str, SeedFood],
) -> str:
    """Slug a name, disambiguating duplicates with the source row id."""
    slug = slugify(name)
    if slug not in taken:
        return slug
    candidate = f"{slug}_{raw_id}"
    counter = 1
    while candidate in taken:
        counter += 1
        candidate = f"{slug}_{raw_id}_{counter}"
    return candidate


def _to_float(value: str | None, food_name: str) -> float:
    """Parse a nutrition value, failing loudly on malformed input."""
    try:
        return float(value or "")
    except ValueError as exc:
        raise ValueError(
            f"Invalid nutrition value {value!r} for food '{food_name}'"
        ) from exc
