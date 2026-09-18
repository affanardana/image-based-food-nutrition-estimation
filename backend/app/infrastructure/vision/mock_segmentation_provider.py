"""MockSegmentationProvider — deterministic fake segmentation for development."""

from dataclasses import replace

from app.domain.entities.segment import Segment
from app.domain.interfaces.vision_provider import VisionProvider


class MockSegmentationProvider(VisionProvider):
    """A deterministic mock vision provider for development and demos.

    Returns a fixed list of segments for any image. Honors the
    suggest_labels toggle: when enabled, segments keep their configured
    suggestions; when disabled, all suggestions are stripped.
    """

    def __init__(self, segments: list[Segment]) -> None:
        self._segments = segments

    def segment(
        self,
        image_path: str,
        suggest_labels: bool = False,
        namespace: str = "",
    ) -> list[Segment]:
        segments = [
            replace(
                segment,
                crop_image_ref=(
                    f"/api/v1/images/crops/{namespace}{segment.segment_id}.jpg"
                ),
            )
            for segment in self._segments
        ]
        if suggest_labels:
            return segments
        return [replace(segment, suggestion=None) for segment in segments]

    @property
    def provider_name(self) -> str:
        return "mock_segmentation"

    @property
    def provider_version(self) -> str:
        return "0.1.0"
