"""SAM3SegmentationProvider — real segmentation backed by SAM 3 + depth.

Follows the owner's reference implementation:
    SAM3SemanticPredictor with text prompts → masks, boxes, classes
    YOLO depth model → raw depth map
    Eq 2: A_norm = mask_px / bbox_area
    Eq 3: D_norm = min-max normalized depth
    Eq 4 input: max D_norm inside each mask

The heavy ultralytics imports are deferred into _get_predictor and the
depth estimator so this module imports (and unit tests run) without
torch/ultralytics installed.

Implementation note: SAM's semantic predictor always needs a prompt
vocabulary — the canonical food catalog provides it. The suggest_labels
toggle controls whether class hints are attached to segments, not the
prompting itself. A true class-agnostic auto-mask mode is a future
provider-internal change.
"""

import logging
from dataclasses import dataclass
from typing import Any, cast

import cv2
import numpy as np
from numpy.typing import NDArray

from app.domain.entities.segment import Segment, SegmentSuggestion
from app.domain.entities.vision_class import VisionClass
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog
from app.domain.interfaces.storage_provider import StorageProvider
from app.domain.interfaces.vision_provider import VisionProvider
from app.domain.values.bounding_box import BoundingBox
from app.domain.values.confidence_score import ConfidenceScore
from app.infrastructure.vision.crop_utils import save_masked_crop
from app.infrastructure.vision.depth import DepthEstimator, resolve_device
from app.infrastructure.vision.mask_stats import (
    clamp_box,
    compute_normalized_area,
    max_depth_in_mask,
    normalize_depth_map,
)
from app.infrastructure.vision.prompts import NOT_FOOD_LABEL, build_prompts

logger = logging.getLogger(__name__)


def confidence_values(
    boxes_conf: NDArray[np.floating] | None,
    count: int,
) -> list[float]:
    """Return per-box confidences, defaulting to 1.0 when unavailable.

    Some SAM3 semantic results carry no confidence scores; a missing
    score must not crash the provider or block suggestions.
    """
    if boxes_conf is None:
        return [1.0] * count
    return [float(value) for value in boxes_conf]


@dataclass(frozen=True)
class SamOutput:
    """Raw SAM output extracted from the ultralytics result object.

    A plain-data seam so the provider logic is testable without models.
    """

    masks: list[NDArray[np.uint8]]
    boxes_xyxy: list[tuple[float, float, float, float]]
    class_ids: list[int]
    class_names: dict[int, str]
    confidences: list[float]


class SAM3SegmentationProvider(VisionProvider):
    """Segments meal images with SAM 3 and YOLO depth estimation."""

    def __init__(
        self,
        sam_model_path: str,
        depth_estimator: DepthEstimator,
        storage_provider: StorageProvider,
        catalog: CanonicalFoodCatalog,
        device: str = "auto",
        confidence_threshold: float = 0.25,
    ) -> None:
        self._sam_model_path = sam_model_path
        self._depth_estimator = depth_estimator
        self._storage_provider = storage_provider
        self._catalog = catalog
        self._device = device
        self._confidence_threshold = confidence_threshold
        self._sam_predictor: Any | None = None

    def segment(
        self,
        image_path: str,
        suggest_labels: bool = False,
        namespace: str = "",
    ) -> list[Segment]:
        """Segment an image into crop regions with mask statistics.

        The canonical food names are used as SAM text prompts. When
        suggest_labels is enabled, each segment carries its matched
        class as an optional suggestion.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image '{image_path}'")
        image_array = cast(NDArray[np.uint8], image)
        height, width = image_array.shape[:2]

        prompts = self._build_prompts()
        output = self._run_sam(image_path, prompts)

        raw_depth = self._depth_estimator.estimate(image_path, (width, height))
        depth_norm = normalize_depth_map(raw_depth)

        segments: list[Segment] = []
        for index, mask in enumerate(output.masks):
            if output.class_names.get(output.class_ids[index]) == NOT_FOOD_LABEL:
                continue

            x1, y1, x2, y2 = output.boxes_xyxy[index]
            x1_clamped, y1_clamped, x2_clamped, y2_clamped = clamp_box(
                x1, y1, x2, y2, width, height
            )
            bbox = BoundingBox(
                x=x1_clamped,
                y=y1_clamped,
                width=max(1, x2_clamped - x1_clamped),
                height=max(1, y2_clamped - y1_clamped),
            )
            area_norm = compute_normalized_area(
                mask,
                (x2_clamped - x1_clamped) * (y2_clamped - y1_clamped),
            )
            max_dnorm = max_depth_in_mask(depth_norm, mask)

            segment_id = f"seg_{index + 1:03d}"
            crop_ref = save_masked_crop(
                image_array,
                mask,
                (x1_clamped, y1_clamped, x2_clamped, y2_clamped),
                self._storage_provider,
                segment_id,
                namespace,
            )

            suggestion = None
            if suggest_labels:
                confidence = float(output.confidences[index])
                suggestion = SegmentSuggestion(
                    vision_class=VisionClass(
                        label=output.class_names[output.class_ids[index]]
                    ),
                    confidence=ConfidenceScore(
                        value=min(max(confidence, 0.0), 1.0)
                    ),
                )

            segments.append(
                Segment(
                    segment_id=segment_id,
                    crop_image_ref=crop_ref,
                    mask_area_px=float(mask.sum()),
                    normalized_area=area_norm,
                    bounding_box=bbox,
                    max_normalized_depth=max_dnorm,
                    provider_name=self.provider_name,
                    provider_version=self.provider_version,
                    suggestion=suggestion,
                )
            )

        logger.info(
            "SAM3 segmentation produced %d food segments", len(segments)
        )
        return segments

    @property
    def provider_name(self) -> str:
        return "sam3_segmentation"

    @property
    def provider_version(self) -> str:
        return "0.1.0"

    # ── Internal helpers ───────────────────────────────────────────────

    def _build_prompts(self) -> list[str]:
        """The prompt vocabulary: canonical food names plus 'not_food'."""
        return build_prompts(self._catalog)

    def _run_sam(self, image_path: str, prompts: list[str]) -> SamOutput:
        """Run SAM3 and extract plain-data output (ultralytics deferred)."""
        try:
            predictor = self._get_predictor()
            predictor.set_image(image_path)
            result = predictor(text=prompts)[0]
        except Exception as exc:
            # Model-layer failures must not leak into the API layer
            # (e.g. ultralytics raising ValueError for device errors).
            raise RuntimeError(f"SAM3 inference failed: {exc}") from exc

        if result.masks is None:
            return SamOutput(
                masks=[],
                boxes_xyxy=[],
                class_ids=[],
                class_names=result.names,
                confidences=[],
            )

        masks = result.masks.data.cpu().numpy().astype(np.uint8)
        boxes_xyxy = result.boxes.xyxy.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        confidences = confidence_values(result.boxes.conf, len(class_ids))

        return SamOutput(
            masks=[masks[i] for i in range(masks.shape[0])],
            boxes_xyxy=[
                (float(row[0]), float(row[1]), float(row[2]), float(row[3]))
                for row in boxes_xyxy
            ],
            class_ids=class_ids.tolist(),
            class_names=result.names,
            confidences=confidences,
        )

    def _get_predictor(self) -> Any:
        """Lazily construct the SAM3 semantic predictor."""
        if self._sam_predictor is None:
            from ultralytics.models.sam import SAM3SemanticPredictor

            self._sam_predictor = SAM3SemanticPredictor(
                overrides={
                    "conf": self._confidence_threshold,
                    "task": "segment",
                    "mode": "predict",
                    "model": self._sam_model_path,
                    "save": False,
                    "device": resolve_device(self._device),
                }
            )
        return self._sam_predictor
