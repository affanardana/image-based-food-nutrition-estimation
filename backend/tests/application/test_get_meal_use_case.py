"""Tests for GetMealUseCase."""

import pytest

from app.application.use_cases.get_meal import GetMealUseCase
from app.domain.entities.meal import Meal
from app.domain.exceptions import MealNotFoundError
from tests.application.fakes import FakeMealRepository


class TestGetMealUseCase:
    def test_returns_existing_meal(self) -> None:
        repo = FakeMealRepository()
        meal = Meal(meal_id="meal_001", image_path="/storage/img.jpg")
        repo.save(meal)
        use_case = GetMealUseCase(repo)

        result = use_case.execute("meal_001")

        assert result is meal
        assert result.meal_id == "meal_001"

    def test_missing_meal_raises(self) -> None:
        use_case = GetMealUseCase(FakeMealRepository())

        with pytest.raises(MealNotFoundError, match="meal_999"):
            use_case.execute("meal_999")
