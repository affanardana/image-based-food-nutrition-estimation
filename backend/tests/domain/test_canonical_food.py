"""Tests for CanonicalFood entity."""

from app.domain.entities.canonical_food import CanonicalFood


class TestCanonicalFood:
    def test_create(self) -> None:
        cf = CanonicalFood(id="burger", name="Burger")
        assert cf.id == "burger"
        assert cf.name == "Burger"

    def test_default_weight(self) -> None:
        cf = CanonicalFood(id="burger", name="Burger")
        assert cf.typical_weight_g == 150.0

    def test_custom_weight(self) -> None:
        cf = CanonicalFood(id="pizza", name="Pizza", typical_weight_g=200.0)
        assert cf.typical_weight_g == 200.0

    def test_typical_weight_as_value_object(self) -> None:
        cf = CanonicalFood(id="rice", name="Rice", typical_weight_g=200.0)
        w = cf.typical_weight
        assert w.value_g == 200.0

    def test_str(self) -> None:
        cf = CanonicalFood(id="burger", name="Burger")
        assert str(cf) == "Burger"

    def test_equality(self) -> None:
        a = CanonicalFood(id="burger", name="Burger")
        b = CanonicalFood(id="burger", name="Burger")
        assert a == b
