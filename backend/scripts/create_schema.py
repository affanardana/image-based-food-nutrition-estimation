"""Create any missing tables in the configured database.

Unlike the food-database seed, this touches no data: it only applies
`metadata.create_all`, which creates tables that do not exist yet and
leaves existing ones (and their rows) alone.

    uv run python scripts/create_schema.py
    uv run python scripts/create_schema.py --database-url "postgresql://..."

`create_all` cannot add a column to a table that already exists. During
development, when a meal table changes shape, drop and recreate just the
meal tables (the food catalog is untouched):

    uv run python scripts/create_schema.py --drop-meal-tables

The database URL defaults to $DATABASE_URL.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import Engine

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.schema import metadata

# Everything else in the metadata belongs to the meal aggregate.
FOOD_TABLES = {"canonical_foods", "nutrition_entries", "vision_labels"}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="SQLAlchemy database URL (default: DATABASE_URL)",
    )
    parser.add_argument(
        "--drop-meal-tables",
        action="store_true",
        help=(
            "Drop the meal tables before creating them. Destroys every "
            "saved meal; the food catalog is untouched."
        ),
    )
    return parser.parse_args()


def meal_tables() -> list[str]:
    """Names of the tables that belong to the meal aggregate."""
    return sorted(
        name for name in metadata.tables if name not in FOOD_TABLES
    )


def drop_meal_tables(engine: Engine) -> None:
    """Remove the meal tables so they can be recreated with a new shape."""
    tables = [metadata.tables[name] for name in meal_tables()]
    metadata.drop_all(engine, tables=tables)


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit(
            "Missing database URL. Pass --database-url or set DATABASE_URL."
        )
    engine = create_database_engine(args.database_url)
    if args.drop_meal_tables:
        drop_meal_tables(engine)
        print(f"Dropped meal tables: {', '.join(meal_tables())}")
    metadata.create_all(engine)
    print(f"Schema up to date on {args.database_url.split('@')[-1]}")
    print(f"Tables: {', '.join(sorted(metadata.tables))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
