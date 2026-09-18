"""NutritionSource entity — an external nutrition database."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NutritionSource:
    """Represents an external nutrition database or provider.

    Examples: Panganku, USDA, Manual Dataset.
    NutritionSource provides nutrition information but does not define business entities.
    """

    name: str
    provider: str

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"
