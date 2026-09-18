"""Tests for MeasurementEstimator — the paper-based portion formulas."""

from app.application.services.measurement_estimator import MeasurementEstimator
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.physical_property import PhysicalProperty
from tests.helpers import make_segment

SATE = CanonicalFood(
    id="sate",
    name="Sate",
    typical_weight_g=100.0,
    physical_properties=PhysicalProperty(
        density_g_per_cm3=0.95,
        calibration_factor=15.0,
    ),
)

# Per default segment: A_norm = 0.9, max D_norm = 0.6
# h = 15.0 × 0.6 = 9.0 cm  →  V = 0.9 × 9.0 = 8.1 cm³
SINGLE_SEGMENT_VOLUME = 8.1


class TestMeasurementEstimator:
    def test_volume_from_single_segment(self) -> None:
        measurement = MeasurementEstimator().estimate(
            SATE,
            [make_segment("seg_001")],
        )

        assert measurement.volume is not None
        assert measurement.volume.value_cm3 == SINGLE_SEGMENT_VOLUME

    def test_weight_from_density(self) -> None:
        measurement = MeasurementEstimator().estimate(
            SATE,
            [make_segment("seg_001")],
        )

        assert measurement.weight is not None
        # W = 0.95 × 8.1 = 7.695 → 7.7 g
        assert measurement.weight.value_g == 7.7

    def test_volume_aggregates_segments(self) -> None:
        measurement = MeasurementEstimator().estimate(
            SATE,
            [make_segment("seg_001"), make_segment("seg_002")],
        )

        assert measurement.volume is not None
        assert measurement.volume.value_cm3 == 16.2
        assert measurement.weight is not None
        # W = 0.95 × 16.2 = 15.39 → 15.4 g
        assert measurement.weight.value_g == 15.4

    def test_no_segments_falls_back_to_typical_weight(self) -> None:
        measurement = MeasurementEstimator().estimate(SATE, [])

        assert measurement.volume is None
        assert measurement.weight is not None
        assert measurement.weight.value_g == 100.0

    def test_no_gamma_falls_back_to_typical_weight(self) -> None:
        food = CanonicalFood(
            id="sate",
            name="Sate",
            typical_weight_g=100.0,
            physical_properties=PhysicalProperty(density_g_per_cm3=0.95),
        )
        measurement = MeasurementEstimator().estimate(
            food,
            [make_segment("seg_001")],
        )

        assert measurement.volume is None
        assert measurement.weight is not None
        assert measurement.weight.value_g == 100.0

    def test_no_density_keeps_volume_but_falls_back_weight(self) -> None:
        food = CanonicalFood(
            id="sate",
            name="Sate",
            typical_weight_g=100.0,
            physical_properties=PhysicalProperty(calibration_factor=15.0),
        )
        measurement = MeasurementEstimator().estimate(
            food,
            [make_segment("seg_001")],
        )

        assert measurement.volume is not None
        assert measurement.volume.value_cm3 == SINGLE_SEGMENT_VOLUME
        assert measurement.weight is not None
        assert measurement.weight.value_g == 100.0

    def test_height_uses_gamma_per_food(self) -> None:
        lontong = CanonicalFood(
            id="lontong",
            name="Lontong",
            typical_weight_g=100.0,
            physical_properties=PhysicalProperty(calibration_factor=25.0),
        )
        measurement = MeasurementEstimator().estimate(
            lontong,
            [make_segment("seg_001")],
        )

        assert measurement.volume is not None
        # h = 25.0 × 0.6 = 15.0 cm  →  V = 0.9 × 15.0 = 13.5 cm³
        assert measurement.volume.value_cm3 == 13.5
