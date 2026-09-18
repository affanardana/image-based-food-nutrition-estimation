"""Physical measurement value objects — Area, Volume, Weight."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Area:
    """Estimated surface area of a food item (square centimeters)."""

    value_cm2: float

    def __post_init__(self) -> None:
        if self.value_cm2 < 0:
            raise ValueError(f"Area must be non-negative, got {self.value_cm2}")


@dataclass(frozen=True)
class Volume:
    """Estimated volume of a food item (cubic centimeters)."""

    value_cm3: float

    def __post_init__(self) -> None:
        if self.value_cm3 < 0:
            raise ValueError(f"Volume must be non-negative, got {self.value_cm3}")


@dataclass(frozen=True)
class Weight:
    """Estimated or user-corrected weight of a food item (grams)."""

    value_g: float

    def __post_init__(self) -> None:
        if self.value_g < 0:
            raise ValueError(f"Weight must be non-negative, got {self.value_g}")
