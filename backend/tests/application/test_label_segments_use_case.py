"""Tests for LabelSegmentsUseCase — labeling workflow and nutrition computation."""

import pytest

from app.application.services.measurement_estimator import MeasurementEstimator
from app.application.services.nutrition_resolver import NutritionResolver
from app.application.use_cases.label_segments import LabelSegmentsUseCase
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.meal import Meal, MealState
from app.domain.entities.physical_property import PhysicalProperty
from app.domain.exceptions import FoodNotFoundError, MealNotFoundError
from app.domain.values.nutrition_values import NutritionProfile
from tests.application.fakes import (
    FakeCatalog,
    FakeMealRepository,
    FakeNutritionProvider,
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
LONTONG = CanonicalFood(
    id="lontong",
    name="Lontong",
    typical_weight_g=100.0,
    physical_properties=PhysicalProperty(
        density_g_per_cm3=0.85,
        calibration_factor=25.0,
    ),
)

PROFILES = {
    "sate": NutritionProfile(
        calories_kcal=218.0,
        protein_g=24.5,
        fat_g=11.2,
        carbohydrates_g=4.8,
    ),
    "lontong": NutritionProfile(
        calories_kcal=130.0,
        protein_g=2.2,
        fat_g=0.4,
        carbohydrates_g=28.5,
    ),
}


def build_use_case(repo: FakeMealRepository) -> LabelSegmentsUseCase:
    """Assemble a LabelSegmentsUseCase with fakes."""
    catalog = FakeCatalog(foods=[SATE, LONTONG], vision_mapping={})
    return LabelSegmentsUseCase(
        meal_repository=repo,
        catalog=catalog,
        nutrition_resolver=NutritionResolver(
            FakeNutritionProvider(PROFILES)
        ),
        measurement_estimator=MeasurementEstimator(),
    )


def make_draft_meal(repo: FakeMealRepository) -> Meal:
    """Create and persist a draft meal with three unlabeled segments."""
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
    return meal


class TestLabelSegmentsUseCase:
    def test_labels_create_food_items_with_nutrition(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        meal = use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "sate",
                    "segment_ids": ["seg_001", "seg_002"],
                },
                {
                    "canonical_food_id": "lontong",
                    "segment_ids": ["seg_003"],
                },
            ],
        )

        assert meal.state == MealState.CORRECTED
        assert len(meal.food_items) == 2

        sate_item = meal.food_items[0]
        assert sate_item.canonical_food is not None
        assert sate_item.canonical_food.id == "sate"
        assert len(sate_item.segments) == 2
        assert sate_item.measurement.volume is not None
        assert sate_item.measurement.volume.value_cm3 == 16.2
        assert sate_item.measurement.weight is not None
        assert sate_item.measurement.weight.value_g == 15.4
        # 218 kcal/100g × (15.4g / 100) = 33.572 kcal
        assert sate_item.nutrition_profile.calories_kcal == pytest.approx(
            33.572, abs=0.01
        )

        lontong_item = meal.food_items[1]
        assert lontong_item.canonical_food is not None
        assert lontong_item.canonical_food.id == "lontong"
        assert lontong_item.measurement.weight is not None
        assert lontong_item.measurement.weight.value_g == 11.5

        # Summary aggregates both items: 33.572 + 14.95 = 48.522 kcal
        assert meal.nutrition_summary.total_calories_kcal == pytest.approx(
            48.52, abs=0.01
        )

    def test_crops_are_retained_not_merged(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        meal = use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "sate",
                    "segment_ids": ["seg_001", "seg_002"],
                }
            ],
        )

        item = meal.food_items[0]
        assert {s.crop_image_ref for s in item.segments} == {
            "/crops/seg_001.jpg",
            "/crops/seg_002.jpg",
        }
        # The meal still owns the original segments
        assert len(meal.segments) == 3

    def test_result_persisted(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "sate",
                    "segment_ids": ["seg_001"],
                }
            ],
        )

        stored = repo.get_by_id("meal_001")
        assert stored is not None
        assert stored.state == MealState.CORRECTED
        assert len(stored.food_items) == 1

    def test_partial_labeling_second_pass(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        use_case.execute(
            "meal_001",
            [{"canonical_food_id": "sate", "segment_ids": ["seg_001"]}],
        )
        meal = use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "lontong",
                    "segment_ids": ["seg_002", "seg_003"],
                }
            ],
        )

        assert len(meal.food_items) == 2
        assert meal.unlabeled_segments == []

    def test_unknown_meal_raises(self) -> None:
        use_case = build_use_case(FakeMealRepository())

        with pytest.raises(MealNotFoundError):
            use_case.execute("missing_meal", [])

    def test_unknown_food_raises(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        with pytest.raises(FoodNotFoundError, match="bakso"):
            use_case.execute(
                "meal_001",
                [
                    {
                        "canonical_food_id": "bakso",
                        "segment_ids": ["seg_001"],
                    }
                ],
            )


class TestNamingWithLabels:
    def test_name_is_applied_with_the_labels(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        meal = use_case.execute(
            "meal_001",
            [{"canonical_food_id": "sate", "segment_ids": ["seg_001"]}],
            name="  Lunch  ",
        )

        assert meal.name == "Lunch"

    def test_omitting_the_name_leaves_it_untouched(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        meal = use_case.execute(
            "meal_001",
            [{"canonical_food_id": "sate", "segment_ids": ["seg_001"]}],
        )

        assert meal.name == ""


class TestReplaceLabels:
    """The edit flow: rebuilding the labeling of a stored meal."""

    def test_replace_rebuilds_items_and_recomputes_nutrition(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)
        use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "sate",
                    "segment_ids": ["seg_001"],
                }
            ],
        )

        meal = use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "lontong",
                    "segment_ids": ["seg_001", "seg_002", "seg_003"],
                }
            ],
            replace=True,
        )

        assert len(meal.food_items) == 1
        item = meal.food_items[0]
        assert item.canonical_food is not None
        assert item.canonical_food.id == "lontong"
        assert len(item.segments) == 3
        assert item.measurement.weight is not None
        # Lontong: 3 segments × (0.9 × 25.0 × 0.6) = 40.5 cm³ × 0.85 g/cm³
        assert item.measurement.weight.value_g == pytest.approx(34.4, abs=0.1)
        # 130 kcal/100g × (34.4 / 100) = 44.7 kcal
        assert meal.nutrition_summary.total_calories_kcal == pytest.approx(
            44.7, abs=0.1
        )

    def test_replace_can_drop_a_food(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)
        use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "sate",
                    "segment_ids": ["seg_001"],
                },
                {
                    "canonical_food_id": "lontong",
                    "segment_ids": ["seg_002"],
                },
            ],
        )

        meal = use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "sate",
                    "segment_ids": ["seg_001"],
                }
            ],
            replace=True,
        )

        assert len(meal.food_items) == 1
        assert [s.segment_id for s in meal.unlabeled_segments] == [
            "seg_002",
            "seg_003",
        ]

    def test_failed_replace_keeps_the_stored_labeling(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)
        use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "sate",
                    "segment_ids": ["seg_001"],
                }
            ],
        )

        with pytest.raises(ValueError, match="not found in meal"):
            use_case.execute(
                "meal_001",
                [
                    {
                        "canonical_food_id": "lontong",
                        "segment_ids": ["seg_999"],
                    }
                ],
                replace=True,
            )

        stored = repo.get_by_id("meal_001")
        assert stored is not None
        assert len(stored.food_items) == 1
        assert stored.food_items[0].canonical_food is not None
        assert stored.food_items[0].canonical_food.id == "sate"

    def test_replace_result_is_persisted(self) -> None:
        repo = FakeMealRepository()
        make_draft_meal(repo)
        use_case = build_use_case(repo)

        use_case.execute(
            "meal_001",
            [
                {
                    "canonical_food_id": "lontong",
                    "segment_ids": ["seg_001", "seg_002"],
                }
            ],
            replace=True,
        )

        stored = repo.get_by_id("meal_001")
        assert stored is not None
        assert len(stored.food_items) == 1
        assert stored.state == MealState.CORRECTED
