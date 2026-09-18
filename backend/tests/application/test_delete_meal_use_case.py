"""Tests for DeleteMealUseCase."""

import pytest

from app.application.use_cases.delete_meal import DeleteMealUseCase
from app.domain.entities.meal import Meal
from app.domain.exceptions import MealNotFoundError
from tests.application.fakes import FakeMealRepository, FakeStorageProvider


class TestDeleteMealUseCase:
    def test_deletes_meal_and_image(self) -> None:
        repo = FakeMealRepository()
        storage = FakeStorageProvider()
        repo.save(Meal(meal_id="meal_001", image_path="/storage/img.jpg"))
        use_case = DeleteMealUseCase(repo, storage)

        use_case.execute("meal_001")

        assert repo.get_by_id("meal_001") is None
        assert "/storage/img.jpg" in storage.deleted

    def test_missing_meal_raises(self) -> None:
        use_case = DeleteMealUseCase(
            FakeMealRepository(),
            FakeStorageProvider(),
        )

        with pytest.raises(MealNotFoundError):
            use_case.execute("missing_meal")
