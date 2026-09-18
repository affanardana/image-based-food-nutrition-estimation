"""Segment entity — one segmented region of a meal image (vision observation)."""

from dataclasses import dataclass

from app.domain.entities.vision_class import VisionClass
from app.domain.values.bounding_box import BoundingBox
from app.domain.values.confidence_score import ConfidenceScore


@dataclass(frozen=True)
class SegmentSuggestion:
    """An optional label suggestion attached to a segment.

    Suggestions are optional and never authoritative. The user always
    decides the final label.
    """

    vision_class: VisionClass
    confidence: ConfidenceScore


@dataclass(frozen=True)
class Segment:
    """A raw vision observation: one cropped image region and its statistics.

    A Segment is NOT a food identity. It only becomes part of a FoodItem
    after the user assigns a label. A Segment retains its own crop image;
    crop images are never merged into one image.
    """

    segment_id: str
    crop_image_ref: str
    mask_area_px: float
    normalized_area: float
    bounding_box: BoundingBox
    max_normalized_depth: float
    provider_name: str
    provider_version: str
    suggestion: SegmentSuggestion | None = None

    def __post_init__(self) -> None:
        if self.mask_area_px < 0:
            raise ValueError(
                f"mask_area_px must be non-negative, got {self.mask_area_px}"
            )
        if not (0.0 <= self.normalized_area <= 1.0):
            raise ValueError(
                "normalized_area must be between 0.0 and 1.0, "
                f"got {self.normalized_area}"
            )
        if not (0.0 <= self.max_normalized_depth <= 1.0):
            raise ValueError(
                "max_normalized_depth must be between 0.0 and 1.0, "
                f"got {self.max_normalized_depth}"
            )
