"""Create and load the food database (canonical foods + nutrition).

Loads data/nutrition.csv (the broad food database) and merges the
curated foods from mappings/canonical_foods.yaml (physical properties,
VisionClass mappings) and data/nutrition_database.yaml (curated
nutrition).

This is a full refresh: existing food rows are replaced.

    uv run python scripts/seed_food_database.py
    uv run python scripts/seed_food_database.py --dry-run
    uv run python scripts/seed_food_database.py --database-url "postgresql://..."

The database URL defaults to $DATABASE_URL — for Supabase, copy the
session-pooler connection string from the project's Connect panel.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import Engine, func, select

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.catalog.sql_canonical_food_catalog import (
    SqlCanonicalFoodCatalog,
)
from app.infrastructure.nutrition.sql_nutrition_provider import (
    SqlNutritionProvider,
)
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.food_seed import (
    apply_seed_data,
    build_seed_data,
)
from app.infrastructure.persistence.schema import (
    canonical_foods,
    nutrition_entries,
    vision_labels,
)

BASE_DIR = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="SQLAlchemy database URL (default: DATABASE_URL)",
    )
    parser.add_argument(
        "--csv",
        default=str(BASE_DIR / "data" / "nutrition.csv"),
        help="Nutrition CSV file",
    )
    parser.add_argument(
        "--mappings",
        default=str(BASE_DIR / "mappings" / "canonical_foods.yaml"),
        help="Curated canonical food mappings",
    )
    parser.add_argument(
        "--curated-nutrition",
        default=str(BASE_DIR / "data" / "nutrition_database.yaml"),
        help="Curated nutrition database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the sources and report counts without writing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = build_seed_data(
        args.csv,
        args.mappings,
        args.curated_nutrition,
    )
    print(
        f"Parsed {len(data.foods)} foods, "
        f"{len(data.nutrition)} nutrition entries, "
        f"{len(data.vision_labels)} vision labels"
    )
    if args.dry_run:
        print("Dry run: nothing written.")
        return 0

    if not args.database_url:
        raise SystemExit(
            "Missing database URL. Pass --database-url or set DATABASE_URL."
        )
    engine = create_database_engine(args.database_url)
    apply_seed_data(engine, data)
    print(f"Seeded {len(data.foods)} foods into {args.database_url.split('@')[-1]}")
    report_database(engine)
    return 0


def report_database(engine: Engine) -> None:
    """Read the seeded data back through the application's providers."""
    with engine.connect() as connection:
        counts = {
            "foods": connection.execute(
                select(func.count()).select_from(canonical_foods)
            ).scalar_one(),
            "nutrition entries": connection.execute(
                select(func.count()).select_from(nutrition_entries)
            ).scalar_one(),
            "vision labels": connection.execute(
                select(func.count()).select_from(vision_labels)
            ).scalar_one(),
        }
    summary = ", ".join(f"{value} {name}" for name, value in counts.items())
    print(f"Verified in database: {summary}")

    catalog = SqlCanonicalFoodCatalog(engine)
    detectable = catalog.list_detectable_foods()
    print(f"Detectable by the vision model: {len(detectable)} foods")
    sample = catalog.get_by_id("sate")
    if sample is None:
        print("Sample lookup: 'sate' not found")
        return
    profile = SqlNutritionProvider(engine).get_nutrition_per_100g(sample)
    print(
        f"Sample lookup: {sample.name} -> "
        f"{profile.calories_kcal:.1f} kcal/100g, "
        f"density={sample.physical_properties.density_g_per_cm3}, "
        f"gamma={sample.physical_properties.calibration_factor}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
