#!/usr/bin/env bash
#
# Download the two checkpoints into ./models, where docker-compose
# bind-mounts them. Run once, from this directory; re-running skips files
# that are already present.
#
#     export HF_TOKEN=hf_xxxxxxxx
#     bash fetch-models.sh
#
# The SAM 3 repository is gated: request access on Hugging Face, create a
# read token, and export it first.
#
# Nothing is installed on this host. The Hugging Face download runs in
# the service image, which already carries huggingface_hub — so a shared
# machine only gets a container, not new system packages.
#
# The token is only needed here. Nothing at runtime reads it, and the
# image never sees it: pass it per-run. Revoke it once the download
# finishes.

set -euo pipefail

cd "$(dirname "$0")"
mkdir -p models

DEPTH_URL="https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26x-depth.pt"

if [ -f models/yolo26x-depth.pt ]; then
    echo "yolo26x-depth.pt already present, skipping"
else
    echo "Downloading the depth model..."
    curl -fL --retry 3 --progress-bar \
        -o models/yolo26x-depth.pt \
        "$DEPTH_URL"
fi

if [ -f models/sam3.pt ]; then
    echo "sam3.pt already present, skipping"
else
    if [ -z "${HF_TOKEN:-}" ]; then
        echo "HF_TOKEN is not set. facebook/sam3 is gated; export a read token first." >&2
        exit 1
    fi
    echo "Building the service image (needed to run the download)..."
    docker compose build vision
    echo "Downloading SAM 3..."
    docker compose run --rm \
        -e HF_TOKEN="$HF_TOKEN" \
        vision \
        python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(repo_id='facebook/sam3', filename='sam3.pt', local_dir='/models')
"
fi

# The download caches the token inside the models directory. Remove it:
# the weights are all that is needed afterwards, and this directory sits
# on a host other people can read as root.
rm -f models/.cache/huggingface/token

echo
echo "Checkpoints in ./models:"
ls -lh models/*.pt
