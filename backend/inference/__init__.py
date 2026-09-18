"""Standalone vision inference service (SAM3 + YOLO depth).

Deliberately outside the `app` package: this code runs in a separate
container with its own dependency set (torch/ultralytics) and is served
by a deployment wrapper — `scripts/remote_vision_server.py` on a local
GPU host, `scripts/modal_vision_server.py` on Modal.com.
"""
