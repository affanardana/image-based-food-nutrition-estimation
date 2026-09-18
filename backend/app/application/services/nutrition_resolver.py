"""NutritionResolver — converts provider data and measurements into nutrition profiles."""

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.measurement import Measurement
from app.domain.interfaces.nutrition_provider import NutritionProvider
from app.domain.values.nutrition_values import NutritionProfile


class NutritionResolver:
    """Resolves the actual nutrition of a food item from its measurement.

    The provider supplies raw nutrition data per 100 grams. This service
    applies the business rule of scaling that data to the measured weight
    (falling back to the canonical food's typical weight when the weight
    has not been measured or corrected).
    """

    def __init__(self, provider: NutritionProvider) -> None:
        self._provider = provider

    def resolve(
        self,
        canonical_food: CanonicalFood,
        measurement: Measurement,
    ) -> NutritionProfile:
        """Resolve the nutrition profile for a food item.

        Args:
            canonical_food: The standardized food entity.
            measurement: Estimated or corrected measurements.

        Returns:
            NutritionProfile scaled to the actual weight.
        """
        per_100g = self._provider.get_nutrition_per_100g(canonical_food)
        weight_g = self._resolve_weight_g(canonical_food, measurement)
        return per_100g.scale(weight_g / 100.0)

    @staticmethod
    def _resolve_weight_g(
        canonical_food: CanonicalFood,
        measurement: Measurement,
    ) -> float:
        if measurement.weight is not None:
            return measurement.weight.value_g
        return canonical_food.typical_weight_g
