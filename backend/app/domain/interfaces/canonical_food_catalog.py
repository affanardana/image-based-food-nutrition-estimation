"""CanonicalFoodCatalog interface — the canonical food registry and mapping."""

from abc import ABC, abstractmethod

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.vision_class import VisionClass


class CanonicalFoodCatalog(ABC):
    """Interface for the canonical food registry.

    Provides the VisionClass → CanonicalFood mapping required by the
    business rules, plus lookup and search for the correction workflow.
    """

    @abstractmethod
    def map_from_vision_class(
        self,
        vision_class: VisionClass,
    ) -> CanonicalFood | None:
        """Map a vision class label to its canonical food.

        Returns None if no mapping exists for the given label.
        """
        ...

    @abstractmethod
    def get_by_id(self, canonical_food_id: str) -> CanonicalFood | None:
        """Retrieve a canonical food by its unique identifier.

        Returns None if the food does not exist.
        """
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 20) -> list[CanonicalFood]:
        """Search canonical foods by name or id, case-insensitive.

        Substring matching, but names that *start* with the keyword rank
        first, so an autocomplete for "ri" suggests "Rice" before
        "Keripik". Ties break alphabetically.

        Args:
            query: Search keyword. An empty query returns all foods.
            limit: Maximum number of results.

        Returns:
            Matching canonical foods, most relevant first.
        """
        ...

    @abstractmethod
    def list_detectable_foods(self) -> list[CanonicalFood]:
        """Foods that carry at least one VisionClass mapping.

        These are the foods a vision provider may prompt with, and the
        only ones that can receive a label suggestion. The catalog may
        hold far more foods than the vision model can detect, so vision
        providers must never prompt with the full catalog.

        Returns:
            Detectable canonical foods, ordered by name.
        """
        ...
