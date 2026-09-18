"""Measurement entity — estimated geometric properties of a food item."""

from dataclasses import dataclass

from app.domain.values.measurement_values import Area, Volume, Weight


@dataclass
class Measurement:
    """Physical measurements for a single food item.

    Values may be estimated or manually corrected.
    """

    area: Area | None = None
    volume: Volume | None = None
    weight: Weight | None = None

    def update_weight(self, weight: Weight) -> None:
        """Update (correct) the weight measurement."""
        self.weight = weight

    def update_volume(self, volume: Volume) -> None:
        """Update (correct) the volume measurement."""
        self.volume = volume

    def update_area(self, area: Area) -> None:
        """Update (correct) the area measurement."""
        self.area = area
