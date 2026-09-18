"""Tests for BoundingBox value object."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.values.bounding_box import BoundingBox


class TestBoundingBox:
    def test_valid_bbox(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=200)
        assert bbox.x == 0
        assert bbox.y == 0
        assert bbox.width == 100
        assert bbox.height == 200

    def test_negative_x_raises(self) -> None:
        with pytest.raises(ValueError, match="x must be non-negative"):
            BoundingBox(x=-1, y=0, width=100, height=100)

    def test_negative_y_raises(self) -> None:
        with pytest.raises(ValueError, match="y must be non-negative"):
            BoundingBox(x=0, y=-1, width=100, height=100)

    def test_zero_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width must be positive"):
            BoundingBox(x=0, y=0, width=0, height=100)

    def test_zero_height_raises(self) -> None:
        with pytest.raises(ValueError, match="height must be positive"):
            BoundingBox(x=0, y=0, width=100, height=0)

    def test_area(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=200)
        assert bbox.area == 20_000

    def test_center(self) -> None:
        bbox = BoundingBox(x=10, y=20, width=100, height=80)
        assert bbox.center_x == 60.0
        assert bbox.center_y == 60.0

    def test_immutable(self) -> None:
        bbox = BoundingBox(x=0, y=0, width=100, height=100)
        with pytest.raises(FrozenInstanceError):
            bbox.width = 50  # type: ignore[misc]

    def test_equality(self) -> None:
        a = BoundingBox(x=0, y=0, width=100, height=100)
        b = BoundingBox(x=0, y=0, width=100, height=100)
        assert a == b
