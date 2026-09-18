"""FoodItem entity — one labeled group of segments within a meal."""

from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.ingredient import Ingredient, IngredientSource
from app.domain.entities.measurement import Measurement
from app.domain.entities.segment import Segment
from app.domain.entities.user_correction import UserCorrection
from app.domain.values.measurement_values import Weight
from app.domain.values.nutrition_values import NutritionProfile


class CorrectionState(StrEnum):
    """Indicates whether a food item has been modified after labeling."""

    LABELED = "labeled"
    USER_CORRECTED = "user_corrected"


@dataclass
class FoodItem:
    """A labeled group of segments representing one food in a meal.

    Created when the user assigns one canonical food to one or more
    segments. Crop images are never merged — the FoodItem references
    its segments, and only the computation aggregates their measurements.
    """

    food_item_id: str
    canonical_food: CanonicalFood | None = None
    segments: list[Segment] = field(default_factory=list)
    measurement: Measurement = field(default_factory=Measurement)
    ingredients: list[Ingredient] = field(default_factory=list)
    nutrition_profile: NutritionProfile = field(default_factory=NutritionProfile)
    correction_state: CorrectionState = CorrectionState.LABELED
    corrections: list[UserCorrection] = field(default_factory=list)

    # ── Correction Operations ──────────────────────────────────────────

    def change_canonical_food(self, new_food: CanonicalFood) -> None:
        """Replace the canonical food (correction)."""
        old = str(self.canonical_food) if self.canonical_food else "none"
        self.canonical_food = new_food
        self.correction_state = CorrectionState.USER_CORRECTED
        self.corrections.append(
            UserCorrection(
                field="canonical_food",
                old_value=old,
                new_value=str(new_food),
            )
        )

    def update_weight(self, weight: Weight) -> None:
        """Correct the estimated weight."""
        old = (
            f"{self.measurement.weight.value_g:.0f}g"
            if self.measurement.weight
            else "none"
        )
        self.measurement.update_weight(weight)
        self.correction_state = CorrectionState.USER_CORRECTED
        self.corrections.append(
            UserCorrection(
                field="weight",
                old_value=old,
                new_value=f"{weight.value_g:.0f}g",
            )
        )

    def replace_ingredients(self, names: list[str]) -> None:
        """Replace the ingredient list with user-provided ingredients."""
        old = ", ".join(i.name for i in self.ingredients) or "none"
        self.ingredients = [
            Ingredient(name=name, source=IngredientSource.MANUAL)
            for name in names
        ]
        self.correction_state = CorrectionState.USER_CORRECTED
        self.corrections.append(
            UserCorrection(
                field="ingredients",
                old_value=old,
                new_value=", ".join(names),
            )
        )

    def set_nutrition_profile(self, profile: NutritionProfile) -> None:
        """Set the resolved nutrition profile for this food item."""
        self.nutrition_profile = profile

    def is_corrected(self) -> bool:
        """Return True if the user has modified this food item after labeling."""
        return self.correction_state == CorrectionState.USER_CORRECTED
