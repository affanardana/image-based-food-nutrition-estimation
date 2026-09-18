"""Pure mask statistics used by the SAM3 provider (paper Eqs 2–3).

These functions are numpy-only and unit-testable without any model,
which keeps the heavy ultralytics/torch dependencies out of the
testable core of the real vision provider.
"""

import numpy as np
from numpy.typing import NDArray


def normalize_depth_map(raw: NDArray[np.float64]) -> NDArray[np.float64]:
    """Min-max normalize the raw depth map to [0, 1] (Eq 3).

    A constant map normalizes to all zeros.
    """
    depth_min = float(raw.min())
    depth_max = float(raw.max())
    return (raw - depth_min) / (depth_max - depth_min + 1e-8)


def compute_normalized_area(
    mask: NDArray[np.uint8],
    bbox_area: float,
) -> float:
    """Return A_norm = mask pixels / bounding box area (Eq 2).

    A non-positive box area is degenerate and yields 0.0. Otherwise the
    ratio is clamped to at most 1.0: a mask should be contained in its
    bounding box, but rounding can make the pixel count exceed the box
    area, which would otherwise violate the Segment invariant.
    """
    if bbox_area <= 0:
        return 0.0
    ratio = float(mask.sum()) / bbox_area
    return min(ratio, 1.0)


def clamp_box(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    """Clamp a bounding box to the image bounds, returning ints.

    Model outputs may extend past the image edges; cropping with
    out-of-bounds coordinates is unsafe.
    """
    x1_clamped = max(0, int(x1))
    y1_clamped = max(0, int(y1))
    x2_clamped = min(width, int(x2))
    y2_clamped = min(height, int(y2))
    return x1_clamped, y1_clamped, x2_clamped, y2_clamped


def max_depth_in_mask(
    depth_norm: NDArray[np.float64],
    mask: NDArray[np.uint8],
) -> float:
    """Return the maximum normalized depth inside the mask (Eq 4 input)."""
    values = depth_norm[mask == 1]
    return float(values.max()) if values.size > 0 else 0.0
