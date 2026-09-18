"""Shared builders for tests."""

from app.domain.entities.segment import Segment, SegmentSuggestion
from app.domain.entities.vision_class import VisionClass
from app.domain.values.bounding_box import BoundingBox
from app.domain.values.confidence_score import ConfidenceScore


def make_segment(
    segment_id: str = "seg_001",
    *,
    normalized_area: float = 0.9,
    max_normalized_depth: float = 0.6,
    mask_area_px: float = 45_000.0,
    suggestion_label: str | None = None,
    confidence: float = 0.87,
) -> Segment:
    """Build a Segment with a fixed bounding box and configurable statistics."""
    suggestion = None
    if suggestion_label is not None:
        suggestion = SegmentSuggestion(
            vision_class=VisionClass(label=suggestion_label),
            confidence=ConfidenceScore(value=confidence),
        )
    return Segment(
        segment_id=segment_id,
        crop_image_ref=f"/crops/{segment_id}.jpg",
        mask_area_px=mask_area_px,
        normalized_area=normalized_area,
        bounding_box=BoundingBox(x=0, y=0, width=250, height=200),
        max_normalized_depth=max_normalized_depth,
        provider_name="fake_vision",
        provider_version="1.0.0",
        suggestion=suggestion,
    )
