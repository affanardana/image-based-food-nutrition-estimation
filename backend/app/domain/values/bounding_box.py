"""BoundingBox value object — represents a rectangular region in an image."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """A rectangular bounding box defined by top-left corner and dimensions.

    All coordinates and dimensions must be non-negative integers.
    """

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0:
            raise ValueError(f"x must be non-negative, got {self.x}")
        if self.y < 0:
            raise ValueError(f"y must be non-negative, got {self.y}")
        if self.width <= 0:
            raise ValueError(f"width must be positive, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"height must be positive, got {self.height}")

    @property
    def area(self) -> int:
        """Return the area of the bounding box in pixels."""
        return self.width * self.height

    @property
    def center_x(self) -> float:
        """Return the x-coordinate of the bounding box center."""
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        """Return the y-coordinate of the bounding box center."""
        return self.y + self.height / 2.0
