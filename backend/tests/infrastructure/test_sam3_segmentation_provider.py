"""Tests for SAM3SegmentationProvider — with stubbed SAM output, no models."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.values.bounding_box import BoundingBox
from app.infrastructure.storage.local_storage_provider import (
    LocalStorageProvider,
)
from app.infrastructure.vision.depth import DepthEstimator
from app.infrastructure.vision.sam3_segmentation_provider import (
    SAM3SegmentationProvider,
    SamOutput,
    confidence_values,
)
from tests.application.fakes import FakeCatalog

IMAGE_H, IMAGE_W = 60, 80


class FakeDepthEstimator(DepthEstimator):
    """Returns a fixed depth map."""

    def __init__(self, depth_map: NDArray[np.float64]) -> None:
        self._depth_map = depth_map

    def estimate(
        self,
        image_path: str,
        target_size: tuple[int, int],
    ) -> NDArray[np.float64]:
        return self._depth_map


class StubSAM3Provider(SAM3SegmentationProvider):
    """Provider with _run_sam stubbed out; records the prompts."""

    def __init__(
        self,
        sam_output: SamOutput,
        depth_estimator: DepthEstimator,
        storage_provider: LocalStorageProvider,
        catalog: FakeCatalog,
    ) -> None:
        super().__init__(
            sam_model_path="unused.pt",
            depth_estimator=depth_estimator,
            storage_provider=storage_provider,
            catalog=catalog,
        )
        self._sam_output = sam_output
        self.prompt_calls: list[list[str]] = []

    def _run_sam(self, image_path: str, prompts: list[str]) -> SamOutput:
        self.prompt_calls.append(prompts)
        return self._sam_output


def make_sam_output() -> SamOutput:
    """One sate mask (600 px, bbox 30×20) and one not_food mask."""
    sate_mask = np.zeros((IMAGE_H, IMAGE_W), dtype=np.uint8)
    sate_mask[10:30, 10:40] = 1  # 20 rows × 30 cols = 600 px

    not_food_mask = np.zeros((IMAGE_H, IMAGE_W), dtype=np.uint8)
    not_food_mask[40:50, 40:60] = 1

    return SamOutput(
        masks=[sate_mask, not_food_mask],
        boxes_xyxy=[(10.0, 10.0, 40.0, 30.0), (40.0, 40.0, 60.0, 50.0)],
        class_ids=[0, 1],
        class_names={0: "sate", 1: "not_food"},
        confidences=[0.9, 0.5],
    )


def make_depth_map() -> NDArray[np.float64]:
    """Depth map where the sate mask contains the maximum (1.0)."""
    depth = np.full((IMAGE_H, IMAGE_W), 0.5, dtype=np.float64)
    depth[15, 20] = 1.0  # inside the sate mask
    depth[0, 0] = 0.0  # image-wide minimum
    return depth


def write_test_image(tmp_path: Path) -> str:
    """Write a real decodable PNG with the expected dimensions."""
    image = np.full((IMAGE_H, IMAGE_W, 3), (100, 80, 60), dtype=np.uint8)
    path = tmp_path / "meal.png"
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    encoded.tofile(str(path))
    return str(path)


def make_provider(tmp_path: Path) -> tuple[StubSAM3Provider, Path]:
    """Build the stub provider with local storage under tmp_path."""
    storage_base = tmp_path / "storage"
    catalog = FakeCatalog(
        foods=[CanonicalFood(id="sate", name="Sate")],
        vision_mapping={"sate": "sate"},
    )
    provider = StubSAM3Provider(
        sam_output=make_sam_output(),
        depth_estimator=FakeDepthEstimator(make_depth_map()),
        storage_provider=LocalStorageProvider(str(storage_base)),
        catalog=catalog,
    )
    return provider, storage_base


class TestSAM3SegmentationProvider:
    def test_skips_not_food_and_builds_segment(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)
        image_path = write_test_image(tmp_path)

        segments = provider.segment(image_path)

        assert len(segments) == 1
        segment = segments[0]
        assert segment.segment_id == "seg_001"
        assert segment.bounding_box == BoundingBox(x=10, y=10, width=30, height=20)
        assert segment.mask_area_px == 600.0
        # A_norm = 600 / (30 × 20) = 1.0
        assert segment.normalized_area == 1.0
        # max depth inside mask = 1.0 after normalization (up to the
        # Eq 3 epsilon: 1 / (1 + 1e-8))
        assert segment.max_normalized_depth == pytest.approx(1.0)
        assert segment.suggestion is None  # toggle off by default

    def test_prompts_come_from_catalog(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)
        image_path = write_test_image(tmp_path)

        provider.segment(image_path)

        assert provider.prompt_calls == [["Sate", "not_food"]]

    def test_suggestions_attached_when_enabled(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)
        image_path = write_test_image(tmp_path)

        segments = provider.segment(image_path, suggest_labels=True)

        assert segments[0].suggestion is not None
        assert segments[0].suggestion.vision_class.label == "sate"
        assert segments[0].suggestion.confidence.value == 0.9

    def test_crop_saved_to_storage(self, tmp_path: Path) -> None:
        provider, storage_base = make_provider(tmp_path)
        image_path = write_test_image(tmp_path)

        segments = provider.segment(image_path)

        crop_path = Path(segments[0].crop_image_ref)
        assert crop_path.exists()
        assert crop_path == storage_base / "crops" / "seg_001.jpg"
        # The crop is a decodable image of the expected size
        crop = cv2.imread(str(crop_path))
        assert crop is not None
        assert crop.shape == (20, 30, 3)

    def test_provider_metadata(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)

        assert provider.provider_name == "sam3_segmentation"
        assert provider.provider_version == "0.1.0"

    def test_bbox_clamped_to_image_bounds(self, tmp_path: Path) -> None:
        mask = np.zeros((IMAGE_H, IMAGE_W), dtype=np.uint8)
        mask[10:30, 10:40] = 1  # 600 px
        sam_output = SamOutput(
            masks=[mask],
            boxes_xyxy=[(10.0, 10.0, 90.0, 30.0)],  # x2 beyond image width
            class_ids=[0],
            class_names={0: "sate"},
            confidences=[0.9],
        )
        storage_base = tmp_path / "storage"
        provider = StubSAM3Provider(
            sam_output=sam_output,
            depth_estimator=FakeDepthEstimator(make_depth_map()),
            storage_provider=LocalStorageProvider(str(storage_base)),
            catalog=FakeCatalog(
                foods=[CanonicalFood(id="sate", name="Sate")],
                vision_mapping={"sate": "sate"},
            ),
        )

        segments = provider.segment(write_test_image(tmp_path))

        segment = segments[0]
        assert segment.bounding_box == BoundingBox(x=10, y=10, width=70, height=20)
        # A_norm = 600 / (70 × 20)
        assert segment.normalized_area == 600.0 / 1400.0
        crop_path = Path(segment.crop_image_ref)
        crop = cv2.imread(str(crop_path))
        assert crop is not None
        assert crop.shape == (20, 70, 3)


class TestConfidenceValues:
    def test_none_defaults_to_full_confidence(self) -> None:
        assert confidence_values(None, 3) == [1.0, 1.0, 1.0]

    def test_array_is_converted_to_floats(self) -> None:
        array = np.array([0.5, 0.75], dtype=np.float32)

        assert confidence_values(array, 2) == [0.5, 0.75]
