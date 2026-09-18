"""Tests for Measurement entity."""

from app.domain.entities.measurement import Measurement
from app.domain.values.measurement_values import Area, Volume, Weight


class TestMeasurement:
    def test_default_empty(self) -> None:
        m = Measurement()
        assert m.area is None
        assert m.weight is None

    def test_with_weight(self) -> None:
        m = Measurement(weight=Weight(value_g=185.0))
        assert m.weight is not None
        assert m.weight.value_g == 185.0

    def test_update_weight(self) -> None:
        m = Measurement(weight=Weight(value_g=150.0))
        m.update_weight(Weight(value_g=200.0))
        assert m.weight.value_g == 200.0  # type: ignore[union-attr]

    def test_update_volume(self) -> None:
        m = Measurement()
        m.update_volume(Volume(value_cm3=300.0))
        assert m.volume.value_cm3 == 300.0  # type: ignore[union-attr]

    def test_update_area(self) -> None:
        m = Measurement()
        m.update_area(Area(value_cm2=50.0))
        assert m.area.value_cm2 == 50.0  # type: ignore[union-attr]
