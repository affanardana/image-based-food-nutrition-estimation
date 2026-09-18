"""ConfidenceScore value object — represents model prediction confidence."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceScore:
    """A confidence value between 0.0 and 1.0 from an AI prediction.

    Raises:
        ValueError: If value is outside the [0.0, 1.0] range.
    """

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(
                f"ConfidenceScore must be between 0.0 and 1.0, got {self.value}"
            )

    def __str__(self) -> str:
        return f"{self.value:.2%}"

    @property
    def percentage(self) -> float:
        """Return confidence as a percentage (0–100)."""
        return self.value * 100.0
