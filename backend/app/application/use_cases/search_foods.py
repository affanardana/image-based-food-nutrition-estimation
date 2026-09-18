"""SearchFoods use case — searches the canonical food catalog."""

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog

DEFAULT_SEARCH_LIMIT: int = 20


class SearchFoodsUseCase:
    """Searches available canonical foods (used by the correction UI)."""

    def __init__(self, catalog: CanonicalFoodCatalog) -> None:
        self._catalog = catalog

    def execute(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[CanonicalFood]:
        """Search canonical foods by keyword.

        Args:
            query: Search keyword (case-insensitive). Empty returns all.
            limit: Maximum number of results.

        Returns:
            Matching canonical foods.
        """
        return self._catalog.search(query, limit=limit)
