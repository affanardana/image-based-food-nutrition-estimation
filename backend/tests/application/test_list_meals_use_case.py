"""Tests for ListMealsUseCase — the meal history."""

from datetime import UTC, datetime, timedelta

from app.application.use_cases.list_meals import ListMealsUseCase
from app.domain.entities.meal import Meal
from tests.application.fakes import FakeMealRepository

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def make_meal(meal_id: str, created_at: datetime) -> Meal:
    """Build a minimal stored meal."""
    return Meal(
        meal_id=meal_id,
        image_path=f"/storage/{meal_id}.jpg",
        created_at=created_at,
        updated_at=created_at,
    )


def make_repository(count: int = 3) -> FakeMealRepository:
    """A repository holding meals an hour apart, oldest first."""
    repository = FakeMealRepository()
    for index in range(count):
        repository.save(
            make_meal(f"meal_{index}", BASE_TIME + timedelta(hours=index))
        )
    return repository


class TestListMealsUseCase:
    def test_returns_meals_newest_first(self) -> None:
        use_case = ListMealsUseCase(make_repository())

        meals = use_case.execute()

        assert [meal.meal_id for meal in meals] == [
            "meal_2",
            "meal_1",
            "meal_0",
        ]

    def test_limit_and_offset(self) -> None:
        use_case = ListMealsUseCase(make_repository())

        meals = use_case.execute(limit=1, offset=1)

        assert [meal.meal_id for meal in meals] == ["meal_1"]

    def test_empty_history(self) -> None:
        use_case = ListMealsUseCase(FakeMealRepository())

        assert use_case.execute() == []

    def test_offset_beyond_history_returns_empty(self) -> None:
        use_case = ListMealsUseCase(make_repository())

        assert use_case.execute(offset=10) == []
