"""Tests for PhysicalProperty entity."""

import pytest

from app.domain.entities.physical_property import PhysicalProperty


class TestPhysicalProperty:
    def test_default_empty(self) -> None:
        pp = PhysicalProperty()
        assert pp.density_g_per_cm3 is None

    def test_with_density(self) -> None:
        pp = PhysicalProperty(density_g_per_cm3=0.95)
        assert pp.density_g_per_cm3 == 0.95

    def test_negative_density_raises(self) -> None:
        with pytest.raises(ValueError, match="Density must be positive"):
            PhysicalProperty(density_g_per_cm3=-0.1)

    def test_estimate_weight_with_density(self) -> None:
        pp = PhysicalProperty(density_g_per_cm3=0.95)
        w = pp.estimate_weight(volume_cm3=200.0)
        assert w == 190.0  # 200 * 0.95

    def test_estimate_weight_without_density(self) -> None:
        pp = PhysicalProperty()
        assert pp.estimate_weight(100.0) is None

    def test_estimate_volume_with_coefficient(self) -> None:
        pp = PhysicalProperty(volume_coefficient=1.5)
        v = pp.estimate_volume(area_cm2=100.0)
        assert v == 150.0

    def test_estimate_volume_without_coefficient(self) -> None:
        pp = PhysicalProperty()
        assert pp.estimate_volume(100.0) is None
