"""Depth estimation — infrastructure-internal abstraction.

Depth estimation is composed inside vision providers; it does not cross
the domain boundary, so this abstraction lives in infrastructure. The
heavy ultralytics import is deferred into the estimate call so the
module remains importable without torch/ultralytics installed.
"""

from abc import ABC, abstractmethod
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray


def resolve_device(device: str) -> str:
    """Resolve 'auto' to a concrete device based on torch availability.

    ultralytics rejects 'auto' on CPU-only machines; the torch import is
    deferred so callers that pass an explicit device stay light.
    """
    if device != "auto":
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


class DepthEstimator(ABC):
    """Produces a raw relative depth map for an image."""

    @abstractmethod
    def estimate(
        self,
        image_path: str,
        target_size: tuple[int, int],
    ) -> NDArray[np.float64]:
        """Return a raw depth map resized to (width, height).

        The map is relative (not metric); normalization happens in the
        vision provider.
        """
        ...


class YOLODepthEstimator(DepthEstimator):
    """Depth estimation via the YOLO depth model (yolo26x-depth)."""

    def __init__(self, model_path: str, device: str = "auto") -> None:
        self._model_path = model_path
        self._device = device
        self._model: Any | None = None

    def estimate(
        self,
        image_path: str,
        target_size: tuple[int, int],
    ) -> NDArray[np.float64]:
        """Run the depth model and resize the map to the image dimensions."""
        from ultralytics import YOLO  # heavy import, deferred

        if self._model is None:
            self._model = YOLO("yolo26x-depth.yaml").load(self._model_path)

        # ultralytics types predict() as a mixed union; cast at the
        # third-party boundary and verify the result defensively.
        results = cast(
            list[Any],
            self._model.predict(
                source=image_path,
                save=False,
                device=resolve_device(self._device),
            ),
        )
        if not results:
            raise RuntimeError(
                f"Depth model returned no results for '{image_path}'"
            )
        depth_result = results[0].depth
        if depth_result is None:
            raise RuntimeError(
                f"Depth model returned no depth map for '{image_path}'"
            )
        depth_map = depth_result.data.squeeze().cpu().numpy()

        width, height = target_size
        if depth_map.shape != (height, width):
            depth_map = cv2.resize(
                depth_map,
                (width, height),
                interpolation=cv2.INTER_CUBIC,
            )
        return np.asarray(depth_map, dtype=np.float64)
