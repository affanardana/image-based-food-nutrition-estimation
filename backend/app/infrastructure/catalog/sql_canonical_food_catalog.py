"""SqlCanonicalFoodCatalog — canonical foods stored in a SQL database.

Production uses Supabase (Postgres); tests use SQLite. The catalog may
hold thousands of foods, of which only those with VisionClass mappings
are detectable by the vision model.
"""

from sqlalchemy import Engine, case, func, or_, select
from sqlalchemy.engine import RowMapping

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.physical_property import PhysicalProperty
from app.domain.entities.vision_class import VisionClass
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog
from app.infrastructure.persistence.schema import (
    canonical_foods,
    vision_labels,
)


class SqlCanonicalFoodCatalog(CanonicalFoodCatalog):
    """Canonical food registry backed by a SQL database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def map_from_vision_class(
        self,
        vision_class: VisionClass,
    ) -> CanonicalFood | None:
        statement = (
            select(canonical_foods)
            .join(
                vision_labels,
                vision_labels.c.canonical_food_id == canonical_foods.c.id,
            )
            .where(vision_labels.c.label == vision_class.label)
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return None if row is None else _to_canonical_food(row)

    def get_by_id(self, canonical_food_id: str) -> CanonicalFood | None:
        statement = select(canonical_foods).where(
            canonical_foods.c.id == canonical_food_id
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return None if row is None else _to_canonical_food(row)

    def search(self, query: str, limit: int = 20) -> list[CanonicalFood]:
        keyword = query.strip().lower()
        statement = select(canonical_foods)
        if keyword:
            name = func.lower(canonical_foods.c.name)
            identifier = func.lower(canonical_foods.c.id)
            statement = statement.where(
                or_(
                    name.like(f"%{keyword}%"),
                    identifier.like(f"%{keyword}%"),
                )
            ).order_by(
                # Names starting with the keyword rank first, so typing
                # "ri" suggests "Rice" before "Keripik".
                case((name.like(f"{keyword}%"), 0), else_=1),
                canonical_foods.c.name,
            )
        else:
            statement = statement.order_by(canonical_foods.c.name)
        statement = statement.limit(limit)
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_to_canonical_food(row) for row in rows]

    def list_detectable_foods(self) -> list[CanonicalFood]:
        statement = (
            select(canonical_foods)
            .join(
                vision_labels,
                vision_labels.c.canonical_food_id == canonical_foods.c.id,
            )
            .distinct()
            .order_by(canonical_foods.c.name)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_to_canonical_food(row) for row in rows]


def _to_canonical_food(row: RowMapping) -> CanonicalFood:
    """Map a canonical_foods row onto the domain entity."""
    return CanonicalFood(
        id=row["id"],
        name=row["name"],
        typical_weight_g=row["typical_weight_g"],
        physical_properties=PhysicalProperty(
            density_g_per_cm3=row["density_g_per_cm3"],
            calibration_factor=row["calibration_factor"],
        ),
    )
