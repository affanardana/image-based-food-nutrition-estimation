"""Deploy the vision inference service to Modal.com.

Runs the shared /segment contract (see inference/vision_service.py) on
Modal with the model checkpoints kept in a Modal Volume, so the
backend's RemoteVisionProvider only needs the deployed URL.

Compute: CPU by default, which runs on Modal's free credits. Setting
GPU_TYPE to "T4" (or another GPU) speeds up inference substantially but
requires a payment method on file, even when spending free credits.

First-time setup (from the backend directory):

    uv run modal deploy scripts/modal_vision_server.py    # prints the app URL

Load the checkpoints into the models volume (once):

    uv run modal run scripts/modal_vision_server.py::fetch_model \\
        --url https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26x-depth.pt \\
        --filename yolo26x-depth.pt

    uv run modal run scripts/modal_vision_server.py::fetch_hf_model \\
        --hf-repo facebook/sam3 --filename sam3.pt

The SAM 3 repository is gated: request access on Hugging Face, create a
read token, and store it as a Modal secret before fetching:

    uv run modal secret create huggingface HF_TOKEN=hf_xxxxxxxx

Local files can also be uploaded directly:

    uv run modal volume put ifne-models ./sam3.pt /sam3.pt

Smoke-test the checkpoints before wiring the backend:

    uv run modal run scripts/modal_vision_server.py::verify_models

Then point the backend at the printed URL:

    $env:VISION_PROVIDER = "remote"
    $env:VISION_REMOTE_URL = "https://<workspace>--ifne-vision-vision-api.modal.run"

Cold starts load both models from the volume (~1 minute); the container
stays warm for `SCALEDOWN_WINDOW_SECONDS` after the last request.
"""

import shutil
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

import modal

if TYPE_CHECKING:
    from fastapi import FastAPI

APP_NAME = "ifne-vision"
MODELS_VOLUME_NAME = "ifne-models"
MODELS_DIR = "/models"
HF_SECRET_NAME = "huggingface"
SAM_FILENAME = "sam3.pt"
DEPTH_FILENAME = "yolo26x-depth.pt"
GPU_TYPE: str | None = None  # e.g. "T4" — requires a payment method on Modal
CPU_CORES = 8.0
MEMORY_MIB = 16384
SCALEDOWN_WINDOW_SECONDS = 300
FUNCTION_TIMEOUT_SECONDS = 600
DOWNLOAD_TIMEOUT_SECONDS = 3600
CPU_TORCH_INDEX = "https://download.pytorch.org/whl/cpu"

app = modal.App(APP_NAME)


def _build_image() -> modal.Image:
    """Build the container image for the configured compute target.

    CPU deployments install CPU-only torch so the image does not carry
    ~2.5 GB of CUDA wheels it cannot use.
    """
    base = modal.Image.debian_slim(python_version="3.12")
    if GPU_TYPE is None:
        base = base.pip_install(
            "torch",
            "torchvision",
            index_url=CPU_TORCH_INDEX,
        )
    else:
        base = base.pip_install("torch", "torchvision")
    return (
        base.pip_install(
            "ultralytics",
            "opencv-python-headless",
            "numpy",
            "fastapi",
            "python-multipart",
            "huggingface_hub",
        )
        # ultralytics depends on the GUI build of OpenCV, which needs
        # libGL — absent from slim images. Remove it and reinstall the
        # headless build so exactly one cv2 package is left in the image.
        .run_commands(
            "pip uninstall -y opencv-python",
            "pip install --no-deps --force-reinstall opencv-python-headless",
        )
        # SAM 3 builds a CLIP text encoder and ultralytics installs its
        # own CLIP fork on first use. That auto-install needs git, which
        # slim images lack, so install the fork at build time and keep
        # runtime auto-install off. The vendored ViT backbone imports
        # timm. Neither package pins torch, so the CPU wheels stay put.
        .apt_install("git")
        .pip_install(
            "git+https://github.com/ultralytics/CLIP.git",
            "timm",
        )
        .env(
            {
                "YOLO_CONFIG_DIR": "/tmp/Ultralytics",
                "YOLO_AUTOINSTALL": "false",
            }
        )
        .add_local_python_source("inference")
    )


def _compute_kwargs() -> dict[str, Any]:
    """Compute resources for the inference container.

    CPU containers need explicit cores and memory: Modal's default
    (0.125 cores / 128 MiB) cannot hold the models. GPU containers use
    Modal's defaults so the GPU is not billed alongside idle CPU.
    """
    if GPU_TYPE is None:
        return {"cpu": CPU_CORES, "memory": MEMORY_MIB}
    return {}


image = _build_image()

models = modal.Volume.from_name(
    MODELS_VOLUME_NAME,
    create_if_missing=True,
)

hf_secret = modal.Secret.from_name(HF_SECRET_NAME, required_keys=["HF_TOKEN"])


def _store(target: Path) -> None:
    """Persist the volume and report the stored checkpoint."""
    models.commit()
    print(f"Stored {target} ({target.stat().st_size / 1e9:.2f} GB)")


@app.function(
    image=image,
    volumes={MODELS_DIR: models},
    timeout=DOWNLOAD_TIMEOUT_SECONDS,
)
def fetch_model(url: str, filename: str) -> None:
    """Download a checkpoint from a public URL into the models volume.

    Args:
        url: Direct download link.
        filename: Destination file name inside the volume.
    """
    target = Path(MODELS_DIR) / filename
    with (
        urllib.request.urlopen(url, timeout=1800) as response,
        open(target, "wb") as destination,
    ):
        shutil.copyfileobj(response, destination)
    _store(target)


@app.function(
    image=image,
    volumes={MODELS_DIR: models},
    timeout=DOWNLOAD_TIMEOUT_SECONDS,
    secrets=[hf_secret],
)
def fetch_hf_model(hf_repo: str, filename: str) -> None:
    """Download a checkpoint from a Hugging Face repository.

    Gated repositories need a read token stored as a Modal secret named
    ``huggingface`` holding ``HF_TOKEN``; huggingface_hub picks the token
    up from the container environment.

    Args:
        hf_repo: Repository id, e.g. ``facebook/sam3``.
        filename: File name inside the repository.
    """
    from huggingface_hub import hf_hub_download

    target = Path(MODELS_DIR) / filename
    downloaded = Path(
        hf_hub_download(
            repo_id=hf_repo,
            filename=filename,
            local_dir=MODELS_DIR,
        )
    )
    if downloaded != target and downloaded.exists():
        shutil.move(str(downloaded), str(target))
    _store(target)


@app.function(
    image=image,
    volumes={MODELS_DIR: models},
    timeout=FUNCTION_TIMEOUT_SECONDS,
    **_compute_kwargs(),
)
def verify_models() -> None:
    """Load both checkpoints and run one inference on a blank image.

    A fast smoke test for the model-loading path: it exercises the same
    code the service uses without waiting on an HTTP cold start.
    """
    import numpy as np

    from inference.vision_service import create_vision_app, run_inference

    service = create_vision_app(
        sam_model_path=f"{MODELS_DIR}/{SAM_FILENAME}",
        depth_model_path=f"{MODELS_DIR}/{DEPTH_FILENAME}",
    )
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    result, depth_map = run_inference(
        service.state,
        image,
        ["food", "not_food"],
    )
    mask_count = 0 if result.masks is None else len(result.masks.data)
    print(f"SAM 3 loaded: {mask_count} masks on a blank image")
    print(
        f"Depth loaded: map {depth_map.shape}, "
        f"range {depth_map.min():.3f}-{depth_map.max():.3f}"
    )


@app.function(
    image=image,
    gpu=GPU_TYPE,
    volumes={MODELS_DIR: models},
    timeout=FUNCTION_TIMEOUT_SECONDS,
    scaledown_window=SCALEDOWN_WINDOW_SECONDS,
    max_containers=1,
    **_compute_kwargs(),
)
@modal.asgi_app()
def vision_api() -> "FastAPI":
    """Serve the shared vision service on Modal."""
    from inference.vision_service import create_vision_app

    return create_vision_app(
        sam_model_path=f"{MODELS_DIR}/{SAM_FILENAME}",
        depth_model_path=f"{MODELS_DIR}/{DEPTH_FILENAME}",
    )
