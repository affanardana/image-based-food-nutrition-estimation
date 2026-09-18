"""Tests for Area, Volume, and Weight value objects."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.values.measurement_values import Area, Volume, Weight


class TestArea:
    def test_valid_area(self) -> None:
        a = Area(value_cm2=50.0)
        assert a.value_cm2 == 50.0

    def test_zero_area(self) -> None:
        a = Area(value_cm2=0.0)
        assert a.value_cm2 == 0.0

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Area(value_cm2=-1.0)

    def test_immutable(self) -> None:
        a = Area(value_cm2=10.0)
        with pytest.raises(FrozenInstanceError):
            a.value_cm2 = 20.0  # type: ignore[misc]


class TestVolume:
    def test_valid_volume(self) -> None:
        v = Volume(value_cm3=200.0)
        assert v.value_cm3 == 200.0

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Volume(value_cm3=-1.0)


class TestWeight:
    def test_valid_weight(self) -> None:
        w = Weight(value_g=185.0)
        assert w.value_g == 185.0

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            Weight(value_g=-1.0)
