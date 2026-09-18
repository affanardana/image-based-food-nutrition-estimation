"""MeasurementEstimator — portion estimation from vision segments (paper-based).

Implements the calibrated portion method selected in ADR-010:

- Height per segment:      h_i = γ × max(D_norm in mask_i)     (Eq 4)
- Volume per segment:      V_i = A_norm_i × h_i                (Eq 5)
- Total volume:            V = Σ V_i
- Weight:                  W = ρ × V                           (Eq 6)

γ (calibration factor) and ρ (density) are per-food physical
properties. The estimation method is intentionally
implementation-dependent (FR-05) and may be replaced.
"""

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.measurement import Measurement
from app.domain.entities.segment import Segment
from app.domain.values.measurement_values import Volume, Weight


class MeasurementEstimator:
    """Estimates volume and weight for a food item from its segments."""

    def estimate(
        self,
        canonical_food: CanonicalFood,
        segments: list[Segment],
    ) -> Measurement:
        """Estimate measurements from the canonical food and its segments.

        Args:
            canonical_food: The labeled canonical food.
            segments: The segments assigned to the food item.

        Returns:
            A Measurement containing estimated volume and weight.
        """
        volume_cm3 = self._estimate_volume_cm3(canonical_food, segments)
        weight_g = self._estimate_weight_g(canonical_food, volume_cm3)

        measurement = Measurement()
        if volume_cm3 is not None:
            measurement.update_volume(Volume(value_cm3=volume_cm3))
        measurement.update_weight(Weight(value_g=weight_g))
        return measurement

    @staticmethod
    def _estimate_volume_cm3(
        canonical_food: CanonicalFood,
        segments: list[Segment],
    ) -> float | None:
        """Sum per-segment volumes: V = Σ(A_norm_i × γ × max_D_norm_i)."""
        gamma = canonical_food.physical_properties.calibration_factor
        if gamma is None or not segments:
            return None
        total = 0.0
        for segment in segments:
            height_cm = gamma * segment.max_normalized_depth
            total += segment.normalized_area * height_cm
        return round(total, 2)

    @staticmethod
    def _estimate_weight_g(
        canonical_food: CanonicalFood,
        volume_cm3: float | None,
    ) -> float:
        """Estimate weight: W = ρ × V, falling back to typical weight."""
        density = canonical_food.physical_properties.density_g_per_cm3
        if volume_cm3 is not None and density is not None:
            return round(density * volume_cm3, 1)
        return canonical_food.typical_weight_g
