"""CanonicalFood entity — the standardized food identity used by the application."""

from dataclasses import dataclass, field

from app.domain.entities.physical_property import PhysicalProperty
from app.domain.values.measurement_values import Weight


@dataclass(frozen=True)
class CanonicalFood:
    """A standardized food entity independent of any dataset or model.

    CanonicalFood is the language of the application. All business logic
    depends on CanonicalFood, never on VisionClass.
    """

    id: str
    name: str
    typical_weight_g: float = 150.0
    physical_properties: PhysicalProperty = field(
        default_factory=PhysicalProperty
    )

    @property
    def typical_weight(self) -> Weight:
        """Return the typical serving weight as a Weight value object."""
        return Weight(value_g=self.typical_weight_g)

    def __str__(self) -> str:
        return self.name
