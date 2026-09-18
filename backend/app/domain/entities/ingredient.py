"""Ingredient entity — a component of a food item."""

from dataclasses import dataclass
from enum import StrEnum


class IngredientSource(StrEnum):
    """Indicates whether an ingredient was predicted by AI or added manually."""

    PREDICTED = "predicted"
    MANUAL = "manual"


@dataclass(frozen=True)
class Ingredient:
    """A single ingredient composing a food item.

    Ingredients are optional. The system must function without them.
    """

    name: str
    source: IngredientSource = IngredientSource.PREDICTED

    def __str__(self) -> str:
        return self.name
