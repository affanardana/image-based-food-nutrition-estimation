"""RemoteVisionProvider — delegates segmentation to a remote inference service.

For development machines without the RAM/GPU to run SAM3 + depth
locally (e.g. a Colab-hosted service). The remote runs the models and
returns raw observations; this provider keeps all paper-methodology
math (Eqs 2-3), mask statistics, and crop saving local, so the rest of
the application is unchanged.

Request (multipart POST /segment):
    image   — the meal image file
    prompts — JSON list of text prompts for the semantic predictor

Response (JSON):
    {
      "status": "success",
      "depth_map": {"height": H, "width": W, "data_base64": "<float32 bytes>"},
      "segments": [
        {
          "mask_data_base64": "<png>",   # grayscale 0/255 mask
          "box_xyxy": [x1, y1, x2, y2],
          "class_id": 0,
          "class_name": "sate",
          "confidence": 0.87
        }
      ]
    }
"""

import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Any, cast
from urllib import error as urlerror
from urllib import request as urlrequest

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
from app.infrastructure.vision.mask_stats import (
    clamp_box,
    compute_normalized_area,
    max_depth_in_mask,
    normalize_depth_map,
)
from app.infrastructure.vision.prompts import NOT_FOOD_LABEL, build_prompts

logger = logging.getLogger(__name__)

SEGMENT_ENDPOINT = "/segment"
REQUEST_TIMEOUT_SECONDS = 600


def _multipart_field(boundary: str, name: str, value: str) -> bytes:
    """Encode one multipart form field."""
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode()


def _multipart_file(
    boundary: str,
    name: str,
    filename: str,
    content: bytes,
) -> bytes:
    """Encode one multipart file part."""
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"; '
        f'filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + content + b"\r\n"


class RemoteVisionProvider(VisionProvider):
    """Vision provider backed by a remote SAM3 + depth inference service."""

    def __init__(
        self,
        base_url: str,
        storage_provider: StorageProvider,
        catalog: CanonicalFoodCatalog,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._storage_provider = storage_provider
        self._catalog = catalog
        self._timeout_seconds = timeout_seconds

    def segment(
        self,
        image_path: str,
        suggest_labels: bool = False,
        namespace: str = "",
    ) -> list[Segment]:
        """Segment an image via the remote service into crop regions."""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image '{image_path}'")
        image_array = cast(NDArray[np.uint8], image)
        height, width = image_array.shape[:2]

        prompts = build_prompts(self._catalog)
        response = self._request(image_path, prompts)

        depth_norm = normalize_depth_map(
            self._decode_depth_map(response, width, height)
        )

        segments: list[Segment] = []
        for index, remote in enumerate(response["segments"]):
            class_name = remote["class_name"]
            if class_name == NOT_FOOD_LABEL:
                continue

            mask = self._decode_mask(remote["mask_data_base64"])
            x1, y1, x2, y2 = remote["box_xyxy"]
            x1c, y1c, x2c, y2c = clamp_box(x1, y1, x2, y2, width, height)
            bbox = BoundingBox(
                x=x1c,
                y=y1c,
                width=max(1, x2c - x1c),
                height=max(1, y2c - y1c),
            )
            area_norm = compute_normalized_area(
                mask,
                (x2c - x1c) * (y2c - y1c),
            )
            max_dnorm = max_depth_in_mask(depth_norm, mask)

            segment_id = f"seg_{index + 1:03d}"
            crop_ref = save_masked_crop(
                image_array,
                mask,
                (x1c, y1c, x2c, y2c),
                self._storage_provider,
                segment_id,
                namespace,
            )

            suggestion = None
            if suggest_labels:
                confidence = float(remote.get("confidence", 1.0))
                suggestion = SegmentSuggestion(
                    vision_class=VisionClass(label=class_name),
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
            "Remote vision produced %d food segments", len(segments)
        )
        return segments

    @property
    def provider_name(self) -> str:
        return "remote_vision"

    @property
    def provider_version(self) -> str:
        return "0.1.0"

    # ── Remote communication ───────────────────────────────────────────

    def _request(self, image_path: str, prompts: list[str]) -> dict[str, Any]:
        """POST the image and prompts, translating transport failures."""
        try:
            payload = self._post(image_path, prompts)
        except (urlerror.URLError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Remote vision request failed: {exc}") from exc

        if payload.get("status") != "success":
            raise RuntimeError(f"Remote vision error: {payload}")
        return payload

    def _post(self, image_path: str, prompts: list[str]) -> dict[str, Any]:
        """Perform the raw multipart POST against the remote service."""
        boundary = uuid.uuid4().hex
        image_bytes = Path(image_path).read_bytes()
        body = b"\r\n".join(
            [
                _multipart_field(boundary, "prompts", json.dumps(prompts)),
                _multipart_file(
                    boundary,
                    "image",
                    Path(image_path).name,
                    image_bytes,
                ),
            ]
        ) + f"\r\n--{boundary}--\r\n".encode()

        http_request = urlrequest.Request(
            f"{self._base_url}{SEGMENT_ENDPOINT}",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}"
            },
            method="POST",
        )
        with urlrequest.urlopen(
            http_request,
            timeout=self._timeout_seconds,
        ) as http_response:
            payload = json.loads(http_response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("Remote vision returned a non-object response")
        return payload

    # ── Response decoding ──────────────────────────────────────────────

    @staticmethod
    def _decode_depth_map(
        response: dict[str, Any],
        width: int,
        height: int,
    ) -> NDArray[np.float64]:
        """Decode the remote depth map, resizing to the image dimensions."""
        spec = response["depth_map"]
        values = np.frombuffer(
            base64.b64decode(spec["data_base64"]),
            dtype=np.float32,
        )
        depth_map = values.reshape(
            spec["height"], spec["width"]
        ).astype(np.float64)
        if depth_map.shape != (height, width):
            resized = cv2.resize(
                depth_map,
                (width, height),
                interpolation=cv2.INTER_CUBIC,
            )
            depth_map = np.asarray(resized, dtype=np.float64)
        return depth_map

    @staticmethod
    def _decode_mask(data_base64: str) -> NDArray[np.uint8]:
        """Decode a base64 PNG mask into a binary uint8 array."""
        encoded = np.frombuffer(base64.b64decode(data_base64), dtype=np.uint8)
        mask = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            raise RuntimeError("Remote vision returned an undecodable mask")
        return np.asarray(mask > 0, dtype=np.uint8)
