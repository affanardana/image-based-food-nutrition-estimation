"""Tests for VisionClass entity."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.entities.vision_class import VisionClass


class TestVisionClass:
    def test_create(self) -> None:
        vc = VisionClass(label="cheeseburger")
        assert vc.label == "cheeseburger"

    def test_str(self) -> None:
        vc = VisionClass(label="burger")
        assert str(vc) == "burger"

    def test_immutable(self) -> None:
        vc = VisionClass(label="pizza")
        with pytest.raises(FrozenInstanceError):
            vc.label = "burger"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert VisionClass(label="burger") == VisionClass(label="burger")

    def test_inequality(self) -> None:
        assert VisionClass(label="burger") != VisionClass(label="pizza")
