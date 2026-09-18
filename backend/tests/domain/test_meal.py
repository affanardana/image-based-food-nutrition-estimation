"""Tests for Meal aggregate root — state transitions and business rules."""

import pytest

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.food_item import FoodItem
from app.domain.entities.meal import FoodItemCorrection, Meal, MealState
from app.domain.values.nutrition_values import NutritionProfile
from tests.helpers import make_segment


def current_state(meal: Meal) -> MealState:
    """Return the meal's current state (defeats mypy enum narrowing)."""
    return meal.state


def make_meal(meal_id: str = "meal_001") -> Meal:
    """Helper to create a meal with one food item."""
    meal = Meal(meal_id=meal_id, image_path="/img/test.jpg")
    food = FoodItem(food_item_id="food_001")
    food.set_nutrition_profile(NutritionProfile(calories_kcal=300.0))
    meal.add_food_item(food)
    return meal


def make_segmented_meal(meal_id: str = "meal_001") -> Meal:
    """Helper to create a draft meal with three unlabeled segments."""
    meal = Meal(meal_id=meal_id, image_path="/img/test.jpg")
    meal.add_segments(
        [
            make_segment("seg_001"),
            make_segment("seg_002"),
            make_segment("seg_003"),
        ]
    )
    meal.mark_draft()
    return meal


class TestMealCreation:
    def test_create_meal(self) -> None:
        meal = Meal(meal_id="meal_001", image_path="/img/test.jpg")
        assert meal.meal_id == "meal_001"
        assert meal.state == MealState.UPLOADED
        assert meal.food_items == []
        assert meal.segments == []

    def test_add_food_item(self) -> None:
        meal = Meal(meal_id="meal_001", image_path="/img/test.jpg")
        food = FoodItem(food_item_id="food_001")
        meal.add_food_item(food)
        assert len(meal.food_items) == 1

    def test_add_segments(self) -> None:
        meal = Meal(meal_id="meal_001", image_path="/img/test.jpg")
        meal.add_segments([make_segment("seg_001"), make_segment("seg_002")])
        assert len(meal.segments) == 2

    def test_remove_food_item(self) -> None:
        meal = make_meal("meal_001")
        meal.remove_food_item("food_001")
        assert len(meal.food_items) == 0

    def test_remove_nonexistent_raises(self) -> None:
        meal = make_meal("meal_001")
        with pytest.raises(ValueError, match="not found"):
            meal.remove_food_item("nonexistent")


class TestMealStateTransitions:
    def test_mark_draft(self) -> None:
        meal = make_meal("meal_001")
        meal.mark_draft()
        assert meal.state == MealState.DRAFT

    def test_cannot_mark_draft_twice(self) -> None:
        meal = make_meal("meal_001")
        meal.mark_draft()
        with pytest.raises(ValueError, match="Cannot transition"):
            meal.mark_draft()

    def test_apply_corrections(self) -> None:
        meal = make_meal("meal_001")
        meal.mark_draft()
        corrections: list[FoodItemCorrection] = [
            {
                "food_item_id": "food_001",
                "canonical_food": CanonicalFood(id="burger", name="Burger"),
                "estimated_weight_g": 210.0,
            }
        ]
        meal.apply_corrections(corrections)
        assert meal.state == MealState.CORRECTED

    def test_cannot_correct_uploaded(self) -> None:
        meal = make_meal("meal_001")
        with pytest.raises(ValueError, match="Cannot correct"):
            meal.apply_corrections([])

    def test_finalize(self) -> None:
        meal = make_meal("meal_001")
        meal.mark_draft()
        meal.apply_corrections([])
        meal.finalize()
        assert meal.state == MealState.FINALIZED

    def test_cannot_finalize_draft(self) -> None:
        meal = make_meal("meal_001")
        meal.mark_draft()
        with pytest.raises(ValueError, match="Cannot finalize"):
            meal.finalize()

    def test_can_apply_multiple_corrections(self) -> None:
        meal = make_meal("meal_001")
        meal.mark_draft()
        meal.apply_corrections([])  # first correction
        meal.apply_corrections([])  # second correction (already corrected state)
        assert meal.state == MealState.CORRECTED


class TestMealLabeling:
    def test_label_single_group(self) -> None:
        meal = make_segmented_meal("meal_001")
        created = meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001", "seg_002"],
                }
            ]
        )

        assert meal.state == MealState.CORRECTED
        assert len(created) == 1
        item = created[0]
        assert item.canonical_food is not None
        assert item.canonical_food.id == "sate"
        assert len(item.segments) == 2
        # Crop references are retained, not merged
        assert {s.crop_image_ref for s in item.segments} == {
            "/crops/seg_001.jpg",
            "/crops/seg_002.jpg",
        }

    def test_label_multiple_groups(self) -> None:
        meal = make_segmented_meal("meal_001")
        created = meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001", "seg_002"],
                },
                {
                    "canonical_food": CanonicalFood(id="lontong", name="Lontong"),
                    "segment_ids": ["seg_003"],
                },
            ]
        )

        assert len(created) == 2
        assert len(meal.food_items) == 2
        assert meal.unlabeled_segments == []

    def test_partial_labeling_allows_second_pass(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )
        # Remaining segments can be labeled in a second pass
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="lontong", name="Lontong"),
                    "segment_ids": ["seg_002", "seg_003"],
                }
            ]
        )
        assert meal.unlabeled_segments == []
        assert len(meal.food_items) == 2

    def test_label_unknown_segment_raises(self) -> None:
        meal = make_segmented_meal("meal_001")
        with pytest.raises(ValueError, match="not found in meal"):
            meal.label_segments(
                [
                    {
                        "canonical_food": CanonicalFood(id="sate", name="Sate"),
                        "segment_ids": ["seg_999"],
                    }
                ]
            )

    def test_label_already_labeled_segment_raises(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )
        with pytest.raises(ValueError, match="already labeled"):
            meal.label_segments(
                [
                    {
                        "canonical_food": CanonicalFood(id="lontong", name="Lontong"),
                        "segment_ids": ["seg_001"],
                    }
                ]
            )

    def test_empty_assignment_raises(self) -> None:
        meal = make_segmented_meal("meal_001")
        with pytest.raises(ValueError, match="at least one segment"):
            meal.label_segments(
                [
                    {
                        "canonical_food": CanonicalFood(id="sate", name="Sate"),
                        "segment_ids": [],
                    }
                ]
            )

    def test_cannot_label_uploaded_meal(self) -> None:
        meal = Meal(meal_id="meal_001", image_path="/img/test.jpg")
        meal.add_segments([make_segment("seg_001")])
        with pytest.raises(ValueError, match="Cannot label"):
            meal.label_segments(
                [
                    {
                        "canonical_food": CanonicalFood(id="sate", name="Sate"),
                        "segment_ids": ["seg_001"],
                    }
                ]
            )

    def test_unlabeled_segments_property(self) -> None:
        meal = make_segmented_meal("meal_001")
        assert len(meal.unlabeled_segments) == 3
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )
        assert [s.segment_id for s in meal.unlabeled_segments] == [
            "seg_002",
            "seg_003",
        ]

    def test_remove_food_item_releases_segments(self) -> None:
        meal = make_segmented_meal("meal_001")
        created = meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )
        meal.remove_food_item(created[0].food_item_id)
        # Segment returns to the unlabeled pool
        assert [s.segment_id for s in meal.unlabeled_segments] == [
            "seg_001",
            "seg_002",
            "seg_003",
        ]


class TestMealBusinessRules:
    def test_nutrition_recalculated_after_correction(self) -> None:
        meal = make_meal("meal_001")
        meal.mark_draft()
        # Before correction
        meal.recalculate_nutrition()
        assert meal.nutrition_summary.total_calories_kcal == 300.0

        # Change food nutrition and apply correction
        meal.food_items[0].set_nutrition_profile(
            NutritionProfile(calories_kcal=500.0)
        )
        meal.apply_corrections([])
        assert meal.nutrition_summary.total_calories_kcal == 500.0

    def test_updated_at_changes_on_operation(self) -> None:
        meal = make_meal("meal_001")
        original = meal.updated_at
        meal.mark_draft()
        assert meal.updated_at > original

    def test_meal_state_lifecycle(self) -> None:
        """Full lifecycle: uploaded → draft → corrected → finalized."""
        meal = Meal(meal_id="meal_lifecycle", image_path="/img/test.jpg")
        assert current_state(meal) == MealState.UPLOADED

        meal.add_segments([make_segment("seg_001")])
        meal.mark_draft()
        assert current_state(meal) == MealState.DRAFT

        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )
        assert current_state(meal) == MealState.CORRECTED

        meal.finalize()
        assert current_state(meal) == MealState.FINALIZED


class TestDiscardSegment:
    """Discarding a bad observation from a meal."""

    def test_discards_unlabeled_segment(self) -> None:
        meal = make_segmented_meal("meal_001")

        discarded = meal.discard_segment("seg_002")

        assert discarded.segment_id == "seg_002"
        assert [s.segment_id for s in meal.segments] == ["seg_001", "seg_003"]

    def test_discarding_a_labeled_segment_updates_its_item(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001", "seg_002"],
                }
            ]
        )

        meal.discard_segment("seg_002")

        assert len(meal.food_items) == 1
        assert [s.segment_id for s in meal.food_items[0].segments] == [
            "seg_001"
        ]

    def test_discarding_the_last_segment_removes_the_item(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )

        meal.discard_segment("seg_001")

        assert meal.food_items == []
        assert [s.segment_id for s in meal.segments] == ["seg_002", "seg_003"]

    def test_unknown_segment_raises(self) -> None:
        meal = make_segmented_meal("meal_001")

        with pytest.raises(ValueError, match="not found in meal"):
            meal.discard_segment("seg_999")

    def test_cannot_discard_from_a_finalized_meal(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )
        meal.finalize()

        with pytest.raises(ValueError, match="Cannot discard"):
            meal.discard_segment("seg_001")


class TestMealRenaming:
    def test_rename_sets_trimmed_name(self) -> None:
        meal = make_meal("meal_001")

        meal.rename("  Lunch  ")

        assert meal.name == "Lunch"

    def test_rename_to_empty_clears_the_name(self) -> None:
        meal = make_meal("meal_001")
        meal.rename("Lunch")

        meal.rename("")

        assert meal.name == ""

    def test_rename_does_not_change_state(self) -> None:
        meal = make_segmented_meal("meal_001")

        meal.rename("Dinner")

        assert current_state(meal) == MealState.DRAFT

    def test_meals_start_unnamed(self) -> None:
        assert Meal(meal_id="m", image_path="/img/x.jpg").name == ""


class TestMealRelabeling:
    """replace_labels — the edit flow for an already-labeled meal."""

    def test_replaces_existing_labeling(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001", "seg_002"],
                }
            ]
        )

        created = meal.replace_labels(
            [
                {
                    "canonical_food": CanonicalFood(id="lontong", name="Lontong"),
                    "segment_ids": ["seg_001", "seg_002", "seg_003"],
                }
            ]
        )

        assert len(created) == 1
        assert len(meal.food_items) == 1
        assert meal.food_items[0].canonical_food is not None
        assert meal.food_items[0].canonical_food.id == "lontong"
        assert len(meal.food_items[0].segments) == 3
        assert current_state(meal) == MealState.CORRECTED

    def test_segments_are_retained(self) -> None:
        meal = make_segmented_meal("meal_001")

        meal.replace_labels(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )

        assert len(meal.segments) == 3
        assert {s.segment_id for s in meal.unlabeled_segments} == {
            "seg_002",
            "seg_003",
        }

    def test_dropping_a_food_releases_its_segments(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                },
                {
                    "canonical_food": CanonicalFood(id="lontong", name="Lontong"),
                    "segment_ids": ["seg_002"],
                },
            ]
        )

        meal.replace_labels(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )

        assert len(meal.food_items) == 1
        assert [s.segment_id for s in meal.unlabeled_segments] == [
            "seg_002",
            "seg_003",
        ]

    def test_unknown_segment_leaves_labeling_untouched(self) -> None:
        meal = make_segmented_meal("meal_001")
        meal.label_segments(
            [
                {
                    "canonical_food": CanonicalFood(id="sate", name="Sate"),
                    "segment_ids": ["seg_001"],
                }
            ]
        )

        with pytest.raises(ValueError, match="not found in meal"):
            meal.replace_labels(
                [
                    {
                        "canonical_food": CanonicalFood(id="lontong", name="Lontong"),
                        "segment_ids": ["seg_999"],
                    }
                ]
            )

        assert len(meal.food_items) == 1
        assert meal.food_items[0].canonical_food is not None
        assert meal.food_items[0].canonical_food.id == "sate"

    def test_segment_claimed_twice_raises(self) -> None:
        meal = make_segmented_meal("meal_001")

        with pytest.raises(ValueError, match="already labeled"):
            meal.replace_labels(
                [
                    {
                        "canonical_food": CanonicalFood(id="sate", name="Sate"),
                        "segment_ids": ["seg_001"],
                    },
                    {
                        "canonical_food": CanonicalFood(id="lontong", name="Lontong"),
                        "segment_ids": ["seg_001"],
                    },
                ]
            )

        assert meal.food_items == []

    def test_cannot_relabel_uploaded_meal(self) -> None:
        meal = Meal(meal_id="meal_001", image_path="/img/test.jpg")
        meal.add_segments([make_segment("seg_001")])

        with pytest.raises(ValueError, match="Cannot relabel"):
            meal.replace_labels(
                [
                    {
                        "canonical_food": CanonicalFood(id="sate", name="Sate"),
                        "segment_ids": ["seg_001"],
                    }
                ]
            )
