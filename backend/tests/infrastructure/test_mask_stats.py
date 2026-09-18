"""Tests for the pure mask-statistics functions (paper Eqs 2–3)."""

import numpy as np
import pytest

from app.infrastructure.vision.mask_stats import (
    clamp_box,
    compute_normalized_area,
    max_depth_in_mask,
    normalize_depth_map,
)


class TestNormalizeDepthMap:
    def test_min_max_normalization(self) -> None:
        raw = np.array([[0.0, 5.0], [10.0, 15.0]], dtype=np.float64)

        normalized = normalize_depth_map(raw)

        assert normalized[0, 0] == pytest.approx(0.0)
        assert normalized[0, 1] == pytest.approx(1.0 / 3.0)
        assert normalized[1, 0] == pytest.approx(2.0 / 3.0)
        assert normalized[1, 1] == pytest.approx(1.0)

    def test_constant_map_normalizes_to_zeros(self) -> None:
        raw = np.full((3, 3), 7.0, dtype=np.float64)

        normalized = normalize_depth_map(raw)

        assert np.all(normalized == 0.0)

    def test_preserves_shape_and_dtype(self) -> None:
        raw = np.zeros((4, 6), dtype=np.float64)

        normalized = normalize_depth_map(raw)

        assert normalized.shape == (4, 6)
        assert normalized.dtype == np.float64


class TestComputeNormalizedArea:
    def test_mask_ratio(self) -> None:
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[0:5, 0:2] = 1  # 10 pixels

        assert compute_normalized_area(mask, bbox_area=40.0) == pytest.approx(0.25)

    def test_zero_bbox_area_returns_zero(self) -> None:
        mask = np.ones((10, 10), dtype=np.uint8)

        assert compute_normalized_area(mask, bbox_area=0.0) == 0.0

    def test_mask_larger_than_bbox_area_is_clamped(self) -> None:
        mask = np.ones((10, 10), dtype=np.uint8)  # 100 px

        assert compute_normalized_area(mask, bbox_area=4.0) == 1.0


class TestMaxDepthInMask:
    def test_returns_maximum_inside_mask(self) -> None:
        depth = np.array([[0.1, 0.9], [0.3, 0.7]], dtype=np.float64)
        mask = np.array([[1, 1], [0, 0]], dtype=np.uint8)

        assert max_depth_in_mask(depth, mask) == pytest.approx(0.9)

    def test_empty_mask_returns_zero(self) -> None:
        depth = np.array([[0.1, 0.9]], dtype=np.float64)
        mask = np.zeros((1, 2), dtype=np.uint8)

        assert max_depth_in_mask(depth, mask) == 0.0


class TestClampBox:
    def test_box_inside_bounds_is_truncated_to_ints(self) -> None:
        assert clamp_box(1.5, 2.5, 10.5, 20.5, 100, 100) == (1, 2, 10, 20)

    def test_box_beyond_edges_is_clamped(self) -> None:
        assert clamp_box(-5.0, -5.0, 120.0, 80.0, 100, 60) == (0, 0, 100, 60)
