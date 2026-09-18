"""Tests for SearchFoodsUseCase."""

from app.application.use_cases.search_foods import SearchFoodsUseCase
from app.domain.entities.canonical_food import CanonicalFood
from tests.application.fakes import FakeCatalog


def make_catalog_with_foods() -> FakeCatalog:
    """Build a catalog with several foods and no vision mapping."""
    foods = [
        CanonicalFood(id="burger", name="Burger"),
        CanonicalFood(id="chicken_burger", name="Chicken Burger"),
        CanonicalFood(id="pizza", name="Pizza"),
    ]
    return FakeCatalog(foods=foods, vision_mapping={})


class TestSearchFoodsUseCase:
    def test_search_matches_by_name(self) -> None:
        use_case = SearchFoodsUseCase(make_catalog_with_foods())

        results = use_case.execute("burger")

        assert [food.id for food in results] == ["burger", "chicken_burger"]

    def test_search_is_case_insensitive(self) -> None:
        use_case = SearchFoodsUseCase(make_catalog_with_foods())

        results = use_case.execute("BURGER")

        assert len(results) == 2

    def test_empty_query_returns_all(self) -> None:
        use_case = SearchFoodsUseCase(make_catalog_with_foods())

        results = use_case.execute("")

        assert len(results) == 3

    def test_limit_is_respected(self) -> None:
        use_case = SearchFoodsUseCase(make_catalog_with_foods())

        results = use_case.execute("", limit=2)

        assert len(results) == 2

    def test_no_match_returns_empty(self) -> None:
        use_case = SearchFoodsUseCase(make_catalog_with_foods())

        results = use_case.execute("sushi")

        assert results == []
