"""Meal aggregate root — the central entity of the application."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TypedDict

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.food_item import FoodItem
from app.domain.entities.nutrition_summary import NutritionSummary
from app.domain.entities.segment import Segment
from app.domain.values.measurement_values import Weight
from app.domain.values.nutrition_values import NutritionProfile


class MealState(StrEnum):
    """The lifecycle state of a meal."""

    UPLOADED = "uploaded"
    DRAFT = "draft"
    CORRECTED = "corrected"
    FINALIZED = "finalized"


class FoodItemCorrection(TypedDict, total=False):
    """A single correction entry applied to one food item.

    canonical_food must be a resolved CanonicalFood entity; the domain
    never resolves identifiers itself.
    """

    food_item_id: str
    canonical_food: CanonicalFood
    estimated_weight_g: float
    ingredients: list[str]


class SegmentLabelAssignment(TypedDict):
    """Assigns one canonical food to one or more unlabeled segments."""

    canonical_food: CanonicalFood
    segment_ids: list[str]


@dataclass
class Meal:
    """Represents a single eating session.

    The Meal is the aggregate root of the domain. It owns the vision
    segments, the labeled FoodItems, the NutritionSummary, and controls
    state transitions. Everything in the application ultimately belongs
    to a Meal.
    """

    meal_id: str
    image_path: str
    segments: list[Segment] = field(default_factory=list)
    food_items: list[FoodItem] = field(default_factory=list)
    nutrition_summary: NutritionSummary = field(default_factory=NutritionSummary)
    state: MealState = MealState.UPLOADED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    name: str = ""

    # ── State Transitions ──────────────────────────────────────────────

    def rename(self, name: str) -> None:
        """Set the meal's display name (an empty string clears it).

        Renaming is metadata: it is allowed in any state and does not
        affect measurements or nutrition.
        """
        self.name = name.strip()
        self._touch()

    def mark_draft(self) -> None:
        """Transition from uploaded to draft after segmentation completes."""
        if self.state != MealState.UPLOADED:
            raise ValueError(
                f"Cannot transition to draft from {self.state.value}"
            )
        self.state = MealState.DRAFT
        self._touch()

    def label_segments(
        self,
        assignments: list[SegmentLabelAssignment],
    ) -> list[FoodItem]:
        """Assign canonical foods to unlabeled segments.

        Segments sharing one label become one FoodItem. Crop images are
        never merged — the FoodItem references its segments, and only the
        computation aggregates their measurements.

        Requires state DRAFT or CORRECTED (partial labeling allowed);
        transitions to CORRECTED.
        """
        if self.state not in (MealState.DRAFT, MealState.CORRECTED):
            raise ValueError(
                f"Cannot label a meal in state {self.state.value}"
            )
        created: list[FoodItem] = []
        for assignment in assignments:
            segments = self._take_unlabeled_segments(
                assignment["segment_ids"]
            )
            item = FoodItem(
                food_item_id=self._generate_food_item_id(),
                canonical_food=assignment["canonical_food"],
                segments=segments,
            )
            self.food_items.append(item)
            created.append(item)
        self.state = MealState.CORRECTED
        self._touch()
        return created

    def replace_labels(
        self,
        assignments: list[SegmentLabelAssignment],
    ) -> list[FoodItem]:
        """Replace the meal's labeling with a new set of assignments.

        Used when editing a stored meal: the existing food items are
        discarded and the same segments are re-grouped. Unlike
        label_segments, already-assigned segments are accepted, because
        here the labeling as a whole is being replaced.

        Requires state DRAFT or CORRECTED; transitions to CORRECTED.

        Raises:
            ValueError: If a segment is unknown or claimed twice. The
                meal is left untouched when validation fails.
        """
        if self.state not in (MealState.DRAFT, MealState.CORRECTED):
            raise ValueError(
                f"Cannot relabel a meal in state {self.state.value}"
            )
        previous_items = self.food_items
        self.food_items = []
        try:
            # label_segments validates every segment id and rolls nothing
            # back itself, so the old items are restored on failure.
            return self.label_segments(assignments)
        except ValueError:
            self.food_items = previous_items
            raise

    def apply_corrections(
        self,
        corrections: list[FoodItemCorrection],
    ) -> None:
        """Apply user corrections to food items and recalculate nutrition.

        Each correction entry may include:
          - food_item_id: str (required)
          - canonical_food: CanonicalFood (optional)
          - estimated_weight_g: float (optional)
          - ingredients: list[str] (optional)
        """
        if self.state not in (MealState.DRAFT, MealState.CORRECTED):
            raise ValueError(
                f"Cannot correct a meal in state {self.state.value}"
            )

        for correction in corrections:
            item = self._find_food_item(correction["food_item_id"])

            if "canonical_food" in correction:
                item.change_canonical_food(correction["canonical_food"])

            if "estimated_weight_g" in correction:
                item.update_weight(
                    Weight(value_g=correction["estimated_weight_g"])
                )

            if "ingredients" in correction:
                item.replace_ingredients(correction["ingredients"])

        self.recalculate_nutrition()
        self.state = MealState.CORRECTED
        self._touch()

    def finalize(self) -> None:
        """Finalize the meal after user confirmation."""
        if self.state != MealState.CORRECTED:
            raise ValueError(
                f"Cannot finalize a meal in state {self.state.value}"
            )
        self.recalculate_nutrition()
        self.state = MealState.FINALIZED
        self._touch()

    # ── Segment & Food Item Management ─────────────────────────────────

    def add_segments(self, segments: list[Segment]) -> None:
        """Attach vision segments produced during analysis."""
        self.segments.extend(segments)
        self._touch()

    def add_food_item(self, item: FoodItem) -> None:
        """Add a food item to the meal (e.g., a manually added food)."""
        self.food_items.append(item)
        self._touch()

    def discard_segment(self, segment_id: str) -> Segment:
        """Drop a segment from the meal.

        Used when a segment is a bad observation — a poor segmentation or
        a food the catalog cannot describe. The segment leaves its food
        item, and an item left with no segments is removed; the crop image
        is the caller's to clean up.

        Requires state DRAFT or CORRECTED.

        Returns:
            The discarded segment.

        Raises:
            ValueError: If the meal is finalized, or the segment is
                unknown.
        """
        if self.state not in (MealState.DRAFT, MealState.CORRECTED):
            raise ValueError(
                f"Cannot discard a segment from a meal in state "
                f"{self.state.value}"
            )
        discarded = next(
            (s for s in self.segments if s.segment_id == segment_id),
            None,
        )
        if discarded is None:
            raise ValueError(f"Segment '{segment_id}' not found in meal")

        self.segments = [
            segment
            for segment in self.segments
            if segment.segment_id != segment_id
        ]
        for item in list(self.food_items):
            if any(s.segment_id == segment_id for s in item.segments):
                item.segments = [
                    segment
                    for segment in item.segments
                    if segment.segment_id != segment_id
                ]
                if not item.segments:
                    self.food_items.remove(item)
        self._touch()
        return discarded

    def remove_food_item(self, food_item_id: str) -> None:
        """Remove a food item by ID.

        Its segments become unlabeled again and may be reassigned.
        """
        item = self._find_food_item(food_item_id)
        self.food_items.remove(item)
        self.recalculate_nutrition()
        self._touch()

    def get_food_item(self, food_item_id: str) -> FoodItem:
        """Retrieve a food item by ID."""
        return self._find_food_item(food_item_id)

    @property
    def unlabeled_segments(self) -> list[Segment]:
        """Return segments that have not been assigned to a food item."""
        assigned_ids = self._assigned_segment_ids()
        return [
            segment
            for segment in self.segments
            if segment.segment_id not in assigned_ids
        ]

    def recalculate_nutrition(self) -> None:
        """Recompute the meal's NutritionSummary from its food items."""
        profiles: list[NutritionProfile] = [
            item.nutrition_profile for item in self.food_items
        ]
        self.nutrition_summary.recalculate(profiles)

    # ── Internal Helpers ───────────────────────────────────────────────

    def _assigned_segment_ids(self) -> set[str]:
        return {
            segment.segment_id
            for item in self.food_items
            for segment in item.segments
        }

    def _take_unlabeled_segments(
        self,
        segment_ids: list[str],
    ) -> list[Segment]:
        if not segment_ids:
            raise ValueError(
                "An assignment must contain at least one segment"
            )
        known = {segment.segment_id: segment for segment in self.segments}
        assigned_ids = self._assigned_segment_ids()
        resolved: list[Segment] = []
        for segment_id in segment_ids:
            segment = known.get(segment_id)
            if segment is None:
                raise ValueError(
                    f"Segment '{segment_id}' not found in meal"
                )
            if segment_id in assigned_ids:
                raise ValueError(
                    f"Segment '{segment_id}' is already labeled"
                )
            resolved.append(segment)
        return resolved

    def _generate_food_item_id(self) -> str:
        return f"food_{uuid.uuid4().hex[:16]}"

    def _find_food_item(self, food_item_id: str) -> FoodItem:
        for item in self.food_items:
            if item.food_item_id == food_item_id:
                return item
        raise ValueError(f"Food item '{food_item_id}' not found in meal")

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC)
