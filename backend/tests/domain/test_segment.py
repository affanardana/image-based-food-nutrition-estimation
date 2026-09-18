"""Tests for Segment entity and SegmentSuggestion."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.entities.segment import Segment, SegmentSuggestion
from app.domain.entities.vision_class import VisionClass
from app.domain.values.bounding_box import BoundingBox
from app.domain.values.confidence_score import ConfidenceScore
from tests.helpers import make_segment


class TestSegment:
    def test_create_without_suggestion(self) -> None:
        segment = make_segment()
        assert segment.segment_id == "seg_001"
        assert segment.crop_image_ref == "/crops/seg_001.jpg"
        assert segment.suggestion is None

    def test_create_with_suggestion(self) -> None:
        segment = make_segment(
            "seg_001",
            suggestion_label="sate",
            confidence=0.87,
        )
        assert segment.suggestion is not None
        assert segment.suggestion.vision_class.label == "sate"
        assert segment.suggestion.confidence.value == 0.87

    def test_negative_mask_area_raises(self) -> None:
        with pytest.raises(ValueError, match="mask_area_px"):
            Segment(
                segment_id="seg_001",
                crop_image_ref="/crops/seg_001.jpg",
                mask_area_px=-1.0,
                normalized_area=0.5,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                max_normalized_depth=0.5,
                provider_name="fake_vision",
                provider_version="1.0.0",
            )

    def test_normalized_area_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="normalized_area"):
            Segment(
                segment_id="seg_001",
                crop_image_ref="/crops/seg_001.jpg",
                mask_area_px=100.0,
                normalized_area=1.5,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                max_normalized_depth=0.5,
                provider_name="fake_vision",
                provider_version="1.0.0",
            )

    def test_negative_normalized_area_raises(self) -> None:
        with pytest.raises(ValueError, match="normalized_area"):
            Segment(
                segment_id="seg_001",
                crop_image_ref="/crops/seg_001.jpg",
                mask_area_px=100.0,
                normalized_area=-0.1,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                max_normalized_depth=0.5,
                provider_name="fake_vision",
                provider_version="1.0.0",
            )

    def test_max_depth_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="max_normalized_depth"):
            Segment(
                segment_id="seg_001",
                crop_image_ref="/crops/seg_001.jpg",
                mask_area_px=100.0,
                normalized_area=0.5,
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                max_normalized_depth=1.2,
                provider_name="fake_vision",
                provider_version="1.0.0",
            )

    def test_immutable(self) -> None:
        segment = make_segment()
        with pytest.raises(FrozenInstanceError):
            segment.normalized_area = 0.5  # type: ignore[misc]

    def test_equality(self) -> None:
        assert make_segment() == make_segment()

    def test_suggestion_equality(self) -> None:
        a = SegmentSuggestion(
            vision_class=VisionClass(label="sate"),
            confidence=ConfidenceScore(value=0.9),
        )
        b = SegmentSuggestion(
            vision_class=VisionClass(label="sate"),
            confidence=ConfidenceScore(value=0.9),
        )
        assert a == b
