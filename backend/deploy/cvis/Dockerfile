# Vision inference service (SAM3 segmentation + YOLO depth).
#
# Runs on CPU. The host's GPU is shared with other people's training jobs
# and is deliberately left alone, so this installs the CPU build of torch
# rather than carrying ~2.5 GB of CUDA wheels it would never use.
#
# Build from the backend directory:
#     docker build -f deploy/cvis/Dockerfile -t ifne-vision .

FROM python:3.12-slim

RUN pip install --no-cache-dir torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
        ultralytics \
        opencv-python-headless \
        numpy \
        fastapi \
        "uvicorn[standard]" \
        python-multipart \
        huggingface_hub

# ultralytics depends on the GUI build of OpenCV, which needs libGL —
# absent from a slim image. Remove it and reinstall the headless build so
# exactly one cv2 package is left installed.
RUN pip uninstall -y opencv-python \
 && pip install --no-deps --force-reinstall opencv-python-headless

# SAM3 builds a CLIP text encoder, and ultralytics installs its own CLIP
# fork on first use — which needs git at runtime. Install both at build
# time and keep runtime auto-install off, so the container never reaches
# the network to fetch a dependency mid-request.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
        git+https://github.com/ultralytics/CLIP.git \
        timm

# Ultralytics writes config to a home directory that may be read-only,
# and the Hugging Face cache lives with the weights so it persists.
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics \
    YOLO_AUTOINSTALL=false \
    HF_HOME=/models/.cache

WORKDIR /service
COPY inference/ ./inference/
COPY deploy/cvis/serve.py ./

EXPOSE 8000
CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8000"]
