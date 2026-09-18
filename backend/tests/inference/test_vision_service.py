"""Tests for the inference service — pure helpers, no models loaded."""

import base64
from types import SimpleNamespace
from typing import Any

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from inference.vision_service import (
    build_segments,
    create_vision_app,
    encode_depth_map,
    encode_mask_png,
    resolve_device,
)


class FakeTensor:
    """Mimics the torch tensor interface used by build_segments."""

    def __init__(self, array: np.ndarray) -> None:
        self._array = array

    def cpu(self) -> "FakeTensor":
        return self

    def numpy(self) -> np.ndarray:
        return self._array


def make_sam_result(
    masks: np.ndarray,
    boxes: np.ndarray,
    class_ids: np.ndarray,
    names: dict[int, str],
    confidences: np.ndarray | None = None,
) -> Any:
    """Build a stand-in for an ultralytics SAM result object."""
    conf_tensor = None if confidences is None else FakeTensor(confidences)
    return SimpleNamespace(
        masks=SimpleNamespace(data=FakeTensor(masks)),
        boxes=SimpleNamespace(
            xyxy=FakeTensor(boxes),
            cls=FakeTensor(class_ids),
            conf=conf_tensor,
        ),
        names=names,
    )


class TestResolveDevice:
    def test_explicit_device_passes_through(self) -> None:
        assert resolve_device("cuda:0") == "cuda:0"


class TestEncodeMaskPng:
    def test_roundtrip_preserves_mask(self) -> None:
        mask = np.zeros((10, 12), dtype=np.uint8)
        mask[2:6, 3:9] = 1

        encoded = encode_mask_png(mask)
        decoded = cv2.imdecode(
            np.frombuffer(base64.b64decode(encoded), dtype=np.uint8),
            cv2.IMREAD_GRAYSCALE,
        )

        assert decoded is not None
        assert decoded.shape == (10, 12)
        np.testing.assert_array_equal((decoded > 0).astype(np.uint8), mask)


class TestEncodeDepthMap:
    def test_encodes_dimensions_and_float32_data(self) -> None:
        depth = np.linspace(0.0, 1.0, 12, dtype=np.float64).reshape(3, 4)

        encoded = encode_depth_map(depth)

        assert encoded["height"] == 3
        assert encoded["width"] == 4
        decoded = np.frombuffer(
            base64.b64decode(encoded["data_base64"]),
            dtype=np.float32,
        ).reshape(3, 4)
        np.testing.assert_allclose(decoded, depth, rtol=1e-6)


class TestBuildSegments:
    def test_builds_one_entry_per_mask(self) -> None:
        masks = np.zeros((2, 8, 8), dtype=np.uint8)
        masks[0, 1:3, 1:3] = 1
        masks[1, 4:6, 4:6] = 1
        result = make_sam_result(
            masks=masks,
            boxes=np.array([[1.0, 1.0, 3.0, 3.0], [4.0, 4.0, 6.0, 6.0]]),
            class_ids=np.array([0, 1]),
            names={0: "sate", 1: "not_food"},
            confidences=np.array([0.9, 0.4]),
        )

        segments = build_segments(result)

        assert [s["class_name"] for s in segments] == ["sate", "not_food"]
        assert segments[0]["box_xyxy"] == [1.0, 1.0, 3.0, 3.0]
        assert segments[0]["confidence"] == pytest.approx(0.9)
        assert segments[0]["mask_data_base64"]

    def test_missing_confidences_default_to_one(self) -> None:
        masks = np.ones((1, 4, 4), dtype=np.uint8)
        result = make_sam_result(
            masks=masks,
            boxes=np.array([[0.0, 0.0, 4.0, 4.0]]),
            class_ids=np.array([0]),
            names={0: "sate"},
        )

        segments = build_segments(result)

        assert segments[0]["confidence"] == 1.0

    def test_no_masks_returns_empty(self) -> None:
        result = SimpleNamespace(masks=None, names={})

        assert build_segments(result) == []


class TestCreateVisionApp:
    def test_health_endpoint_without_models(self) -> None:
        app = create_vision_app("unused.pt", "unused-depth.pt", device="cpu")

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "success", "service": "healthy"}

    def test_device_resolved_on_startup(self) -> None:
        app = create_vision_app("unused.pt", "unused-depth.pt", device="cpu")

        assert app.state.device == "cpu"
        assert app.state.sam_predictor is None
