"""SqlNutritionProvider — nutrition data stored in a SQL database.

Production uses Supabase (Postgres); tests use SQLite. A canonical food
may have entries from several sources (domain rule 5); the configured
source is preferred, and any other entry serves as the fallback.
"""

from sqlalchemy import Engine, case, select
from sqlalchemy.engine import RowMapping

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.exceptions import NutritionUnavailableError
from app.domain.interfaces.nutrition_provider import NutritionProvider
from app.domain.values.nutrition_values import NutritionProfile
from app.infrastructure.persistence.schema import nutrition_entries

DEFAULT_SOURCE = "nutrition_csv"


class SqlNutritionProvider(NutritionProvider):
    """Nutrition lookups from a SQL database."""

    def __init__(
        self,
        engine: Engine,
        source: str = DEFAULT_SOURCE,
    ) -> None:
        self._engine = engine
        self._source = source

    def get_nutrition_per_100g(
        self,
        canonical_food: CanonicalFood,
    ) -> NutritionProfile:
        statement = (
            select(nutrition_entries)
            .where(nutrition_entries.c.canonical_food_id == canonical_food.id)
            .order_by(
                case((nutrition_entries.c.source == self._source, 0), else_=1)
            )
            .limit(1)
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        if row is None:
            raise NutritionUnavailableError(
                f"No nutrition data for '{canonical_food.id}' in database"
            )
        return _to_nutrition_profile(row)

    @property
    def provider_name(self) -> str:
        return "sql"

    @property
    def source(self) -> str:
        """The preferred nutrition source."""
        return self._source


def _to_nutrition_profile(row: RowMapping) -> NutritionProfile:
    """Map a nutrition_entries row onto the value object."""
    return NutritionProfile(
        calories_kcal=row["calories_kcal"],
        protein_g=row["protein_g"],
        fat_g=row["fat_g"],
        carbohydrates_g=row["carbohydrates_g"],
        fiber_g=row["fiber_g"],
        sodium_mg=row["sodium_mg"],
    )
