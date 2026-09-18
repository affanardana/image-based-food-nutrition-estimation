"""PhysicalProperty entity — known physical constants for a CanonicalFood."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicalProperty:
    """Physical constants for a canonical food, used in measurement estimation.

    These values belong to CanonicalFood, not to VisionClass.
    """

    density_g_per_cm3: float | None = None
    calibration_factor: float | None = None
    volume_coefficient: float | None = None

    def __post_init__(self) -> None:
        if self.density_g_per_cm3 is not None and self.density_g_per_cm3 <= 0:
            raise ValueError(
                f"Density must be positive, got {self.density_g_per_cm3}"
            )

    def estimate_weight(self, volume_cm3: float) -> float | None:
        """Estimate weight from volume using density, if available."""
        if self.density_g_per_cm3 is None:
            return None
        return volume_cm3 * self.density_g_per_cm3

    def estimate_volume(self, area_cm2: float) -> float | None:
        """Estimate volume from area using the volume coefficient, if available."""
        if self.volume_coefficient is None:
            return None
        return area_cm2 * self.volume_coefficient
