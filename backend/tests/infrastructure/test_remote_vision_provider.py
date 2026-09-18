"""Tests for RemoteVisionProvider — with a stubbed HTTP transport."""

import base64
from pathlib import Path
from typing import Any
from urllib.error import URLError

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.values.bounding_box import BoundingBox
from app.infrastructure.storage.local_storage_provider import (
    LocalStorageProvider,
)
from app.infrastructure.vision.remote_vision_provider import (
    RemoteVisionProvider,
)
from tests.application.fakes import FakeCatalog

IMAGE_H, IMAGE_W = 60, 80


class StubRemoteProvider(RemoteVisionProvider):
    """Provider with _post stubbed out; records the prompts.

    Error wrapping and status checking in the real _request remain in
    play, so error-path tests exercise production handling.
    """

    def __init__(
        self,
        response: dict[str, Any] | Exception,
        storage_provider: LocalStorageProvider,
        catalog: FakeCatalog,
    ) -> None:
        super().__init__(
            base_url="http://remote.test",
            storage_provider=storage_provider,
            catalog=catalog,
        )
        self._response = response
        self.request_calls: list[tuple[str, list[str]]] = []

    def _post(self, image_path: str, prompts: list[str]) -> dict[str, Any]:
        self.request_calls.append((image_path, prompts))
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def mask_to_png_base64(mask: NDArray[np.uint8]) -> str:
    ok, encoded = cv2.imencode(".png", (mask * 255).astype(np.uint8))
    assert ok
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def depth_to_base64(depth: NDArray[np.float64]) -> dict[str, Any]:
    return {
        "height": int(depth.shape[0]),
        "width": int(depth.shape[1]),
        "data_base64": base64.b64encode(
            depth.astype(np.float32).tobytes()
        ).decode("ascii"),
    }


def make_remote_response() -> dict[str, Any]:
    """One sate mask (600 px, bbox 30x20) and one not_food mask."""
    sate_mask = np.zeros((IMAGE_H, IMAGE_W), dtype=np.uint8)
    sate_mask[10:30, 10:40] = 1

    not_food_mask = np.zeros((IMAGE_H, IMAGE_W), dtype=np.uint8)
    not_food_mask[40:50, 40:60] = 1

    depth = np.full((IMAGE_H, IMAGE_W), 0.5, dtype=np.float64)
    depth[15, 20] = 1.0  # inside the sate mask
    depth[0, 0] = 0.0  # image-wide minimum

    return {
        "status": "success",
        "depth_map": depth_to_base64(depth),
        "segments": [
            {
                "mask_data_base64": mask_to_png_base64(sate_mask),
                "box_xyxy": [10.0, 10.0, 40.0, 30.0],
                "class_id": 0,
                "class_name": "sate",
                "confidence": 0.9,
            },
            {
                "mask_data_base64": mask_to_png_base64(not_food_mask),
                "box_xyxy": [40.0, 40.0, 60.0, 50.0],
                "class_id": 1,
                "class_name": "not_food",
                "confidence": 0.5,
            },
        ],
    }


def write_test_image(tmp_path: Path) -> str:
    """Write a real decodable PNG with the expected dimensions."""
    image = np.full((IMAGE_H, IMAGE_W, 3), (100, 80, 60), dtype=np.uint8)
    path = tmp_path / "meal.png"
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    encoded.tofile(str(path))
    return str(path)


def make_provider(tmp_path: Path) -> tuple[StubRemoteProvider, Path]:
    """Build the stub provider with local storage under tmp_path."""
    storage_base = tmp_path / "storage"
    catalog = FakeCatalog(
        foods=[CanonicalFood(id="sate", name="Sate")],
        vision_mapping={"sate": "sate"},
    )
    provider = StubRemoteProvider(
        response=make_remote_response(),
        storage_provider=LocalStorageProvider(str(storage_base)),
        catalog=catalog,
    )
    return provider, storage_base


class TestRemoteVisionProvider:
    def test_skips_not_food_and_builds_segment(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)

        segments = provider.segment(write_test_image(tmp_path))

        assert len(segments) == 1
        segment = segments[0]
        assert segment.segment_id == "seg_001"
        assert segment.bounding_box == BoundingBox(x=10, y=10, width=30, height=20)
        assert segment.mask_area_px == 600.0
        # A_norm = 600 / (30 x 20) = 1.0
        assert segment.normalized_area == 1.0
        assert segment.max_normalized_depth == pytest.approx(1.0)
        assert segment.suggestion is None  # toggle off by default

    def test_prompts_come_from_catalog(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)

        provider.segment(write_test_image(tmp_path))

        assert provider.request_calls[0][1] == ["Sate", "not_food"]

    def test_suggestions_attached_when_enabled(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)

        segments = provider.segment(
            write_test_image(tmp_path),
            suggest_labels=True,
        )

        assert segments[0].suggestion is not None
        assert segments[0].suggestion.vision_class.label == "sate"
        assert segments[0].suggestion.confidence.value == 0.9

    def test_crop_saved_to_storage(self, tmp_path: Path) -> None:
        provider, storage_base = make_provider(tmp_path)

        segments = provider.segment(write_test_image(tmp_path))

        crop_path = Path(segments[0].crop_image_ref)
        assert crop_path.exists()
        assert crop_path == storage_base / "crops" / "seg_001.jpg"
        crop = cv2.imread(str(crop_path))
        assert crop is not None
        assert crop.shape == (20, 30, 3)

    def test_bbox_clamped_to_image_bounds(self, tmp_path: Path) -> None:
        mask = np.zeros((IMAGE_H, IMAGE_W), dtype=np.uint8)
        mask[10:30, 10:40] = 1  # 600 px
        response = {
            "status": "success",
            "depth_map": depth_to_base64(
                np.full((IMAGE_H, IMAGE_W), 0.5, dtype=np.float64)
            ),
            "segments": [
                {
                    "mask_data_base64": mask_to_png_base64(mask),
                    "box_xyxy": [10.0, 10.0, 90.0, 30.0],  # x2 past width
                    "class_id": 0,
                    "class_name": "sate",
                    "confidence": 0.9,
                }
            ],
        }
        storage_base = tmp_path / "storage"
        provider = StubRemoteProvider(
            response=response,
            storage_provider=LocalStorageProvider(str(storage_base)),
            catalog=FakeCatalog(
                foods=[CanonicalFood(id="sate", name="Sate")],
                vision_mapping={"sate": "sate"},
            ),
        )

        segments = provider.segment(write_test_image(tmp_path))

        segment = segments[0]
        assert segment.bounding_box == BoundingBox(x=10, y=10, width=70, height=20)
        assert segment.normalized_area == 600.0 / 1400.0
        crop = cv2.imread(segments[0].crop_image_ref)
        assert crop is not None
        assert crop.shape == (20, 70, 3)

    def test_http_failure_raises_runtime_error(self, tmp_path: Path) -> None:
        provider = StubRemoteProvider(
            response=URLError("connection refused"),
            storage_provider=LocalStorageProvider(str(tmp_path / "storage")),
            catalog=FakeCatalog(
                foods=[CanonicalFood(id="sate", name="Sate")],
                vision_mapping={"sate": "sate"},
            ),
        )

        with pytest.raises(RuntimeError, match="Remote vision request failed"):
            provider.segment(write_test_image(tmp_path))

    def test_error_status_raises_runtime_error(self, tmp_path: Path) -> None:
        provider = StubRemoteProvider(
            response={"status": "error", "message": "model exploded"},
            storage_provider=LocalStorageProvider(str(tmp_path / "storage")),
            catalog=FakeCatalog(
                foods=[CanonicalFood(id="sate", name="Sate")],
                vision_mapping={"sate": "sate"},
            ),
        )

        with pytest.raises(RuntimeError, match="Remote vision error"):
            provider.segment(write_test_image(tmp_path))

    def test_provider_metadata(self, tmp_path: Path) -> None:
        provider, _ = make_provider(tmp_path)

        assert provider.provider_name == "remote_vision"
        assert provider.provider_version == "0.1.0"
