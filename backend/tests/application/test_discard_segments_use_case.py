"""Tests for DiscardSegmentsUseCase — dropping bad crops."""

import pytest

from app.application.services.measurement_estimator import MeasurementEstimator
from app.application.services.nutrition_resolver import NutritionResolver
from app.application.use_cases.discard_segments import DiscardSegmentsUseCase
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.meal import Meal
from app.domain.entities.physical_property import PhysicalProperty
from app.domain.exceptions import MealNotFoundError
from app.domain.values.nutrition_values import NutritionProfile
from tests.application.fakes import (
    FakeMealRepository,
    FakeNutritionProvider,
    FakeStorageProvider,
)
from tests.helpers import make_segment

SATE = CanonicalFood(
    id="sate",
    name="Sate",
    typical_weight_g=100.0,
    physical_properties=PhysicalProperty(
        density_g_per_cm3=0.95,
        calibration_factor=15.0,
    ),
)
PROFILES = {
    "sate": NutritionProfile(
        calories_kcal=218.0,
        protein_g=24.5,
        fat_g=11.2,
        carbohydrates_g=4.8,
    )
}


def build_use_case(
    repo: FakeMealRepository,
    storage: FakeStorageProvider | None = None,
) -> tuple[DiscardSegmentsUseCase, FakeStorageProvider]:
    """Assemble the use case with fakes."""
    storage_provider = storage or FakeStorageProvider()
    return (
        DiscardSegmentsUseCase(
            meal_repository=repo,
            storage_provider=storage_provider,
            nutrition_resolver=NutritionResolver(
                FakeNutritionProvider(PROFILES)
            ),
            measurement_estimator=MeasurementEstimator(),
        ),
        storage_provider,
    )


def make_labeled_meal(repo: FakeMealRepository) -> Meal:
    """A draft meal with two segments labeled as one food item."""
    meal = Meal(meal_id="meal_001", image_path="/storage/img.jpg")
    meal.add_segments(
        [make_segment("seg_001"), make_segment("seg_002")]
    )
    meal.mark_draft()
    meal.label_segments(
        [{"canonical_food": SATE, "segment_ids": ["seg_001", "seg_002"]}]
    )
    repo.save(meal)
    return meal


class TestDiscardSegmentsUseCase:
    def test_discards_one_segment(self) -> None:
        repo = FakeMealRepository()
        make_labeled_meal(repo)
        use_case, _ = build_use_case(repo)

        meal = use_case.execute("meal_001", ["seg_002"])

        assert [s.segment_id for s in meal.segments] == ["seg_001"]

    def test_discards_several_segments_at_once(self) -> None:
        repo = FakeMealRepository()
        meal = Meal(meal_id="meal_001", image_path="/storage/img.jpg")
        meal.add_segments(
            [
                make_segment("seg_001"),
                make_segment("seg_002"),
                make_segment("seg_003"),
            ]
        )
        meal.mark_draft()
        repo.save(meal)
        use_case, _ = build_use_case(repo)

        updated = use_case.execute("meal_001", ["seg_001", "seg_003"])

        assert [s.segment_id for s in updated.segments] == ["seg_002"]

    def test_recomputes_nutrition_for_the_affected_item(self) -> None:
        repo = FakeMealRepository()
        make_labeled_meal(repo)
        use_case, _ = build_use_case(repo)

        meal = use_case.execute("meal_001", ["seg_002"])

        item = meal.food_items[0]
        assert [s.segment_id for s in item.segments] == ["seg_001"]
        # One segment: 0.9 × (15.0 × 0.6) = 8.1 cm³ × 0.95 g/cm³
        assert item.measurement.weight is not None
        assert item.measurement.weight.value_g == pytest.approx(7.7, abs=0.1)
        assert item.nutrition_profile.calories_kcal == pytest.approx(
            16.8, abs=0.1
        )
        assert meal.nutrition_summary.total_calories_kcal == pytest.approx(
            16.8, abs=0.1
        )

    def test_removes_the_food_item_when_its_last_segment_goes(self) -> None:
        repo = FakeMealRepository()
        make_labeled_meal(repo)
        use_case, _ = build_use_case(repo)

        updated = use_case.execute("meal_001", ["seg_001", "seg_002"])

        assert updated.food_items == []
        assert updated.segments == []
        assert updated.nutrition_summary.total_calories_kcal == 0.0

    def test_deletes_the_crop_files(self) -> None:
        repo = FakeMealRepository()
        meal = make_labeled_meal(repo)
        crop_refs = [segment.crop_image_ref for segment in meal.segments]
        use_case, storage = build_use_case(repo)

        use_case.execute("meal_001", ["seg_001", "seg_002"])

        assert sorted(crop_refs) == sorted(storage.deleted)

    def test_result_is_persisted(self) -> None:
        repo = FakeMealRepository()
        make_labeled_meal(repo)
        use_case, _ = build_use_case(repo)

        use_case.execute("meal_001", ["seg_002"])

        stored = repo.get_by_id("meal_001")
        assert stored is not None
        assert [s.segment_id for s in stored.segments] == ["seg_001"]

    def test_unlabeled_segment_can_be_discarded(self) -> None:
        repo = FakeMealRepository()
        meal = Meal(meal_id="meal_001", image_path="/storage/img.jpg")
        meal.add_segments([make_segment("seg_001")])
        meal.mark_draft()
        repo.save(meal)
        use_case, _ = build_use_case(repo)

        updated = use_case.execute("meal_001", ["seg_001"])

        assert updated.segments == []

    def test_unknown_meal_raises(self) -> None:
        use_case, _ = build_use_case(FakeMealRepository())

        with pytest.raises(MealNotFoundError):
            use_case.execute("missing", ["seg_001"])

    def test_unknown_segment_raises(self) -> None:
        repo = FakeMealRepository()
        make_labeled_meal(repo)
        use_case, _ = build_use_case(repo)

        with pytest.raises(ValueError, match="not found in meal"):
            use_case.execute("meal_001", ["seg_999"])

    def test_nothing_is_discarded_when_one_id_is_unknown(self) -> None:
        repo = FakeMealRepository()
        make_labeled_meal(repo)
        use_case, _ = build_use_case(repo)

        with pytest.raises(ValueError, match="not found in meal"):
            use_case.execute("meal_001", ["seg_001", "seg_999"])

        stored = repo.get_by_id("meal_001")
        assert stored is not None
        assert len(stored.segments) == 2

    def test_empty_list_raises(self) -> None:
        repo = FakeMealRepository()
        make_labeled_meal(repo)
        use_case, _ = build_use_case(repo)

        with pytest.raises(ValueError, match="At least one segment"):
            use_case.execute("meal_001", [])
