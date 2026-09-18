"""Tests for MockSegmentationProvider."""

from app.infrastructure.vision.mock_segmentation_provider import (
    MockSegmentationProvider,
)
from tests.helpers import make_segment


def make_provider() -> MockSegmentationProvider:
    return MockSegmentationProvider(
        [
            make_segment("seg_001", suggestion_label="sate"),
            make_segment("seg_002", suggestion_label="lontong"),
        ]
    )


class TestMockSegmentationProvider:
    def test_suggestions_present_when_enabled(self) -> None:
        segments = make_provider().segment(
            "/img/test.jpg",
            suggest_labels=True,
        )

        assert len(segments) == 2
        assert segments[0].suggestion is not None
        assert segments[0].suggestion.vision_class.label == "sate"

    def test_suggestions_stripped_when_disabled(self) -> None:
        segments = make_provider().segment(
            "/img/test.jpg",
            suggest_labels=False,
        )

        assert len(segments) == 2
        assert all(segment.suggestion is None for segment in segments)

    def test_suggestions_disabled_by_default(self) -> None:
        segments = make_provider().segment("/img/test.jpg")

        assert all(segment.suggestion is None for segment in segments)

    def test_segment_stats_preserved_in_both_modes(self) -> None:
        provider = make_provider()

        with_suggestions = provider.segment("/img/test.jpg", True)
        without_suggestions = provider.segment("/img/test.jpg", False)

        assert with_suggestions[0].segment_id == without_suggestions[0].segment_id
        assert with_suggestions[0].crop_image_ref == without_suggestions[0].crop_image_ref
        assert with_suggestions[0].normalized_area == without_suggestions[0].normalized_area

    def test_provider_metadata(self) -> None:
        provider = make_provider()

        assert provider.provider_name == "mock_segmentation"
        assert provider.provider_version == "0.1.0"
