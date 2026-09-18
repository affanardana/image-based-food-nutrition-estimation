"""Tests for SqlMealRepository — SQLite-backed, no server needed."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, func, select

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.food_item import CorrectionState
from app.domain.entities.meal import Meal, MealState
from app.domain.entities.physical_property import PhysicalProperty
from app.domain.values.measurement_values import Volume, Weight
from app.domain.values.nutrition_values import NutritionProfile
from app.infrastructure.persistence.schema import (
    food_item_corrections,
    food_item_ingredients,
    food_item_segments,
    food_items,
    meals,
    segments,
)
from app.infrastructure.persistence.sql_meal_repository import (
    SqlMealRepository,
)
from tests.helpers import make_segment
from tests.infrastructure.helpers import make_sqlite_engine

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


@pytest.fixture
def engine() -> Engine:
    return make_sqlite_engine()


def make_labeled_meal(
    meal_id: str = "meal_001",
    created_at: datetime | None = None,
) -> Meal:
    """A meal labeled with two segments grouped under one food item."""
    timestamp = created_at or datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    meal = Meal(
        meal_id=meal_id,
        image_path=f"/storage/{meal_id}_plate.jpg",
        created_at=timestamp,
        updated_at=timestamp,
    )
    meal.add_segments(
        [
            make_segment("seg_001", suggestion_label="sate"),
            make_segment("seg_002", suggestion_label="lontong", confidence=0.5),
        ]
    )
    meal.mark_draft()
    item = meal.label_segments(
        [
            {
                "canonical_food": SATE,
                "segment_ids": ["seg_001", "seg_002"],
            }
        ]
    )[0]
    item.measurement.update_volume(Volume(value_cm3=12.5))
    item.measurement.update_weight(Weight(value_g=11.9))
    item.set_nutrition_profile(
        NutritionProfile(
            calories_kcal=25.9,
            protein_g=2.9,
            fat_g=1.3,
            carbohydrates_g=0.6,
        )
    )
    item.replace_ingredients(["Bun", "Patty"])
    meal.recalculate_nutrition()
    return meal


class TestSaveAndGet:
    def test_round_trip_preserves_meal(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        meal = make_labeled_meal()

        repository.save(meal)
        loaded = repository.get_by_id("meal_001")

        assert loaded is not None
        assert loaded.state == MealState.CORRECTED
        assert loaded.image_path == "/storage/meal_001_plate.jpg"
        assert loaded.created_at == meal.created_at
        assert loaded.updated_at == meal.updated_at
        assert len(loaded.segments) == 2
        assert len(loaded.food_items) == 1

        item = loaded.food_items[0]
        assert item.canonical_food is not None
        assert item.canonical_food.id == "sate"
        assert item.canonical_food.name == "Sate"
        assert item.canonical_food.typical_weight_g == 100.0
        snapshot = item.canonical_food.physical_properties
        assert snapshot.density_g_per_cm3 == 0.95
        assert snapshot.calibration_factor == 15.0
        assert [s.segment_id for s in item.segments] == ["seg_001", "seg_002"]
        assert item.measurement.volume is not None
        assert item.measurement.volume.value_cm3 == 12.5
        assert item.measurement.weight is not None
        assert item.measurement.weight.value_g == 11.9
        assert item.nutrition_profile.calories_kcal == 25.9
        assert item.correction_state == CorrectionState.USER_CORRECTED
        assert loaded.nutrition_summary.total_calories_kcal == 25.9

    def test_segment_statistics_and_suggestion_round_trip(
        self,
        engine: Engine,
    ) -> None:
        repository = SqlMealRepository(engine)
        repository.save(make_labeled_meal())

        loaded = repository.get_by_id("meal_001")

        assert loaded is not None
        first = next(s for s in loaded.segments if s.segment_id == "seg_001")
        assert first.bounding_box.width == 250
        assert first.bounding_box.height == 200
        assert first.normalized_area == 0.9
        assert first.max_normalized_depth == 0.6
        assert first.mask_area_px == 45_000.0
        assert first.provider_name == "fake_vision"
        assert first.suggestion is not None
        assert first.suggestion.vision_class.label == "sate"
        assert first.suggestion.confidence.value == 0.87

    def test_missing_meal_returns_none(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)

        assert repository.get_by_id("missing") is None

    def test_name_round_trip(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        meal = make_labeled_meal()
        meal.rename("Lunch with the team")

        repository.save(meal)
        loaded = repository.get_by_id("meal_001")

        assert loaded is not None
        assert loaded.name == "Lunch with the team"

    def test_unnamed_meal_reads_back_empty(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        repository.save(make_labeled_meal())

        loaded = repository.get_by_id("meal_001")

        assert loaded is not None
        assert loaded.name == ""

    def test_food_item_order_is_preserved(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        meal = Meal(meal_id="meal_order", image_path="/storage/order.jpg")
        meal.add_segments([make_segment("seg_001"), make_segment("seg_002")])
        meal.mark_draft()
        meal.label_segments(
            [
                {"canonical_food": SATE, "segment_ids": ["seg_001"]},
                {"canonical_food": LONTONG, "segment_ids": ["seg_002"]},
            ]
        )

        repository.save(meal)
        loaded = repository.get_by_id("meal_order")

        assert loaded is not None
        assert [
            item.canonical_food.id
            for item in loaded.food_items
            if item.canonical_food is not None
        ] == ["sate", "lontong"]

    def test_exists(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        repository.save(make_labeled_meal())

        assert repository.exists("meal_001") is True
        assert repository.exists("meal_002") is False

    def test_meal_without_food_items_round_trips(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        meal = Meal(meal_id="meal_draft", image_path="/storage/draft.jpg")
        meal.add_segments([make_segment("seg_001")])
        meal.mark_draft()

        repository.save(meal)
        loaded = repository.get_by_id("meal_draft")

        assert loaded is not None
        assert loaded.state == MealState.DRAFT
        assert loaded.food_items == []
        assert len(loaded.segments) == 1
        assert loaded.segments[0].suggestion is None


class TestReplacingContent:
    def test_saving_again_replaces_the_stored_version(
        self,
        engine: Engine,
    ) -> None:
        repository = SqlMealRepository(engine)
        meal = make_labeled_meal()
        repository.save(meal)

        meal.replace_labels(
            [{"canonical_food": LONTONG, "segment_ids": ["seg_001"]}]
        )
        repository.save(meal)

        loaded = repository.get_by_id("meal_001")
        assert loaded is not None
        assert len(loaded.food_items) == 1
        assert loaded.food_items[0].canonical_food is not None
        assert loaded.food_items[0].canonical_food.id == "lontong"
        assert [s.segment_id for s in loaded.food_items[0].segments] == [
            "seg_001"
        ]
        # No orphaned rows from the previous version
        with engine.connect() as connection:
            assert connection.execute(
                select(func.count()).select_from(food_items)
            ).scalar_one() == 1
            assert connection.execute(
                select(func.count()).select_from(food_item_segments)
            ).scalar_one() == 1
            assert connection.execute(
                select(func.count()).select_from(food_item_ingredients)
            ).scalar_one() == 0

    def test_corrections_are_persisted(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        repository.save(make_labeled_meal())

        loaded = repository.get_by_id("meal_001")

        assert loaded is not None
        item = loaded.food_items[0]
        fields = [correction.field for correction in item.corrections]
        assert "ingredients" in fields
        assert item.ingredients[0].name == "Bun"


class TestListRecent:
    def test_orders_newest_first(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        base = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
        for index in range(3):
            repository.save(
                make_labeled_meal(
                    meal_id=f"meal_{index}",
                    created_at=base + timedelta(hours=index),
                )
            )

        meals_page = repository.list_recent()

        assert [meal.meal_id for meal in meals_page] == [
            "meal_2",
            "meal_1",
            "meal_0",
        ]

    def test_limit_and_offset(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        base = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
        for index in range(3):
            repository.save(
                make_labeled_meal(
                    meal_id=f"meal_{index}",
                    created_at=base + timedelta(hours=index),
                )
            )

        page = repository.list_recent(limit=1, offset=1)

        assert [meal.meal_id for meal in page] == ["meal_1"]

    def test_empty_history(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)

        assert repository.list_recent() == []

    def test_children_do_not_leak_between_meals(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        repository.save(make_labeled_meal("meal_a"))
        repository.save(make_labeled_meal("meal_b"))

        page = repository.list_recent()

        assert len(page) == 2
        for meal in page:
            assert len(meal.segments) == 2
            assert len(meal.food_items) == 1
            assert {
                segment.segment_id
                for segment in meal.food_items[0].segments
            } == {"seg_001", "seg_002"}


class TestDelete:
    def test_delete_removes_meal_and_children(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        repository.save(make_labeled_meal())

        repository.delete("meal_001")

        assert repository.get_by_id("meal_001") is None
        with engine.connect() as connection:
            for table in (
                meals,
                segments,
                food_items,
                food_item_segments,
                food_item_ingredients,
                food_item_corrections,
            ):
                assert connection.execute(
                    select(func.count()).select_from(table)
                ).scalar_one() == 0, table.name

    def test_delete_missing_meal_is_noop(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)

        repository.delete("missing")  # should not raise

    def test_delete_leaves_other_meals_alone(self, engine: Engine) -> None:
        repository = SqlMealRepository(engine)
        repository.save(make_labeled_meal("meal_a"))
        repository.save(make_labeled_meal("meal_b"))

        repository.delete("meal_a")

        assert repository.get_by_id("meal_a") is None
        assert repository.get_by_id("meal_b") is not None
