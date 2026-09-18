"""Shared crop extraction used by vision providers.

Crops are the masked image region inside the segment's bounding box,
persisted through the StorageProvider. Both the local SAM3 provider and
the RemoteVisionProvider reuse this so crop handling stays identical.
"""

import tempfile
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from app.domain.interfaces.storage_provider import StorageProvider


def save_masked_crop(
    image: NDArray[np.uint8],
    mask: NDArray[np.uint8],
    box: tuple[int, int, int, int],
    storage_provider: StorageProvider,
    segment_id: str,
    namespace: str = "",
) -> str:
    """Save the masked crop region of ``image`` via the storage provider.

    The mask must have the same dimensions as the image. The crop is
    stored as ``crops/{namespace}{segment_id}.jpg``; the namespace (the
    meal id) keeps crops from different meals apart. Returns the storage
    reference, or an empty string when the region is empty.
    """
    x1, y1, x2, y2 = box
    masked = cv2.bitwise_and(image, image, mask=mask)
    crop = masked[y1:y2, x1:x2]
    if crop.size == 0:
        return ""

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        cv2.imwrite(tmp_path, crop)
        return storage_provider.store(
            tmp_path,
            f"crops/{namespace}{segment_id}.jpg",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
