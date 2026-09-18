"""NutritionProvider interface — contract for all nutrition data sources."""

from abc import ABC, abstractmethod

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.values.nutrition_values import NutritionProfile


class NutritionProvider(ABC):
    """Interface that every nutrition data source must implement.

    The provider receives CanonicalFood (never VisionClass) and returns
    raw nutrition data per 100 grams. Weight scaling is a business rule
    handled by the application layer, not by the provider.
    """

    @abstractmethod
    def get_nutrition_per_100g(
        self,
        canonical_food: CanonicalFood,
    ) -> NutritionProfile:
        """Return the nutritional profile per 100 grams of the given food.

        Args:
            canonical_food: The standardized food entity.

        Returns:
            A NutritionProfile containing values per 100 grams.

        Raises:
            NutritionUnavailableError: If the food is not found in this source.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this nutrition provider."""
        ...
