"""UserCorrection entity — records a single manual modification by the user."""

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import UTC, datetime


@dataclass(frozen=True)
class UserCorrection:
    """A single correction made by the user to a food item.

    Corrections are first-class domain objects. They override AI predictions
    and provide an audit trail of user modifications.
    """

    field: str
    old_value: str
    new_value: str
    timestamp: datetime = dataclass_field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __str__(self) -> str:
        return (
            f"Correction({self.field}: '{self.old_value}' → '{self.new_value}')"
        )
