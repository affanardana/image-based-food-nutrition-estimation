"""SAM3 + YOLO depth behind the HTTP contract used by RemoteVisionProvider.

The service is a dumb model runner: it returns raw masks, boxes, class
names, confidences, and the depth map. All portion mathematics stays in
the backend, so every deployment serves the same contract:

    POST /segment   multipart: image (file), prompts (JSON list)
    GET  /health

Deployment wrappers import `create_vision_app`; they never re-implement
it, so the contract cannot drift between hosts.
"""

import base64
import json
import tempfile
from pathlib import Path
from typing import Annotated, Any

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from numpy.typing import NDArray

SAM_CONFIDENCE_THRESHOLD = 0.25
DEFAULT_MASK_CONFIDENCE = 1.0
DEPTH_MODEL_CONFIG = "yolo26x-depth.yaml"


def resolve_device(device: str) -> str:
    """Resolve 'auto' to a concrete device based on torch availability."""
    if device != "auto":
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def encode_mask_png(mask: NDArray[np.uint8]) -> str:
    """Encode a binary mask as a base64 PNG string."""
    ok, encoded = cv2.imencode(".png", (mask * 255).astype(np.uint8))
    if not ok:
        raise RuntimeError("Failed to encode mask as PNG")
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def encode_depth_map(depth_map: NDArray[np.float64]) -> dict[str, Any]:
    """Encode a depth map as base64 float32 bytes with its dimensions."""
    return {
        "height": int(depth_map.shape[0]),
        "width": int(depth_map.shape[1]),
        "data_base64": base64.b64encode(
            depth_map.astype(np.float32).tobytes()
        ).decode("ascii"),
    }


def build_segments(result: Any) -> list[dict[str, Any]]:
    """Extract masks, boxes, classes, and confidences from SAM output."""
    if result.masks is None:
        return []

    masks = result.masks.data.cpu().numpy().astype(np.uint8)
    boxes = result.boxes.xyxy.cpu().numpy()
    class_ids = result.boxes.cls.cpu().numpy().astype(int)
    confidences = (
        result.boxes.conf.cpu().numpy()
        if result.boxes.conf is not None
        else np.full(len(class_ids), DEFAULT_MASK_CONFIDENCE)
    )

    segments: list[dict[str, Any]] = []
    for index in range(masks.shape[0]):
        segments.append(
            {
                "mask_data_base64": encode_mask_png(masks[index]),
                "box_xyxy": [float(value) for value in boxes[index]],
                "class_id": int(class_ids[index]),
                "class_name": result.names[class_ids[index]],
                "confidence": float(confidences[index]),
            }
        )
    return segments


def load_sam_predictor(state: Any) -> Any:
    """Lazily construct the SAM3 semantic predictor (container-scoped)."""
    if state.sam_predictor is None:
        from ultralytics.models.sam import SAM3SemanticPredictor

        state.sam_predictor = SAM3SemanticPredictor(
            overrides={
                "conf": SAM_CONFIDENCE_THRESHOLD,
                "task": "segment",
                "mode": "predict",
                "model": state.sam_model_path,
                "save": False,
                "device": state.device,
            }
        )
    return state.sam_predictor


def load_depth_model(state: Any) -> Any:
    """Lazily construct the YOLO depth model (container-scoped)."""
    if state.depth_model is None:
        from ultralytics import YOLO

        state.depth_model = YOLO(DEPTH_MODEL_CONFIG).load(
            state.depth_model_path
        )
    return state.depth_model


def run_inference(
    state: Any,
    image: NDArray[np.uint8],
    prompts: list[str],
) -> tuple[Any, NDArray[np.float64]]:
    """Run SAM3 + depth on an image and return (SAM result, depth map)."""
    height, width = image.shape[:2]
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        cv2.imwrite(tmp_path, image)

        sam = load_sam_predictor(state)
        sam.set_image(tmp_path)
        result = sam(text=prompts)[0]

        depth_model = load_depth_model(state)
        depth_results = depth_model.predict(
            source=tmp_path,
            save=False,
            device=state.device,
        )
        depth_map = depth_results[0].depth.data.squeeze().cpu().numpy()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if depth_map.shape != (height, width):
        depth_map = cv2.resize(
            depth_map,
            (width, height),
            interpolation=cv2.INTER_CUBIC,
        )
    return result, np.asarray(depth_map, dtype=np.float64)


def create_vision_app(
    sam_model_path: str,
    depth_model_path: str,
    device: str = "auto",
) -> FastAPI:
    """Build the inference service application.

    Models are loaded lazily on the first /segment request so the app
    object itself is free to construct (health checks, tests).
    """
    application = FastAPI(title="I-FNE Vision Service")
    application.state.sam_model_path = sam_model_path
    application.state.depth_model_path = depth_model_path
    application.state.device = resolve_device(device)
    application.state.sam_predictor = None
    application.state.depth_model = None

    @application.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "success", "service": "healthy"}

    @application.post("/segment")
    async def segment(
        request: Request,
        image: Annotated[UploadFile, File()],
        prompts: Annotated[str, Form()],
    ) -> dict[str, Any]:
        """Run SAM3 + depth on the uploaded image and return raw outputs."""
        prompt_list = json.loads(prompts)
        decoded = cv2.imdecode(
            np.frombuffer(await image.read(), dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        if decoded is None:
            raise HTTPException(400, "Could not decode the uploaded image")

        result, depth_map = run_inference(
            request.app.state,
            np.asarray(decoded, dtype=np.uint8),
            prompt_list,
        )
        return {
            "status": "success",
            "depth_map": encode_depth_map(depth_map),
            "segments": build_segments(result),
        }

    return application
