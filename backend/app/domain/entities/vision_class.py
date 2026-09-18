"""VisionClass entity — the raw label predicted by an AI model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VisionClass:
    """A class label produced by a vision model.

    VisionClass is dataset-dependent and must never be used directly
    for nutrition lookup. It must be mapped to a CanonicalFood first.
    """

    label: str

    def __str__(self) -> str:
        return self.label
