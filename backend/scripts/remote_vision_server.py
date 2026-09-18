"""Run the vision inference service on a local GPU host.

Thin wrapper around `inference.vision_service`: serves the shared
/segment + /health contract, optionally behind a cloudflared quick
tunnel when the host has no public address.

    uv run python scripts/remote_vision_server.py \\
        --sam-model sam3.pt --depth-model yolo26x-depth.pt

For a hosted deployment (no local GPU needed) use the Modal app
instead: scripts/modal_vision_server.py.
"""

import argparse
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn

from inference.vision_service import create_vision_app

TUNNEL_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def extract_tunnel_url(line: str) -> str | None:
    """Find a cloudflared trycloudflare URL in a log line."""
    match = TUNNEL_URL_PATTERN.search(line)
    return match.group(0) if match else None


def start_tunnel(port: int) -> None:
    """Stream cloudflared output and announce the public URL."""

    def _run() -> None:
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if process.stdout is None:
            return
        for line in process.stdout:
            print(line, end="", flush=True)
            url = extract_tunnel_url(line)
            if url is not None:
                print(f"\n>>> VISION_REMOTE_URL={url}\n", flush=True)

    threading.Thread(target=_run, daemon=True).start()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments, defaulting model paths to environment variables."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sam-model",
        default=os.getenv("VISION_SAM_MODEL_PATH", ""),
        help="SAM3 checkpoint path (default: VISION_SAM_MODEL_PATH)",
    )
    parser.add_argument(
        "--depth-model",
        default=os.getenv("VISION_DEPTH_MODEL_PATH", ""),
        help="YOLO depth checkpoint path (default: VISION_DEPTH_MODEL_PATH)",
    )
    parser.add_argument(
        "--device",
        default=os.getenv("VISION_DEVICE", "auto"),
        help="Inference device (default: VISION_DEVICE or 'auto')",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--tunnel",
        action="store_true",
        help="Expose the server via a cloudflared quick tunnel",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.sam_model or not args.depth_model:
        raise SystemExit(
            "Missing model paths. Pass --sam-model/--depth-model or set "
            "VISION_SAM_MODEL_PATH/VISION_DEPTH_MODEL_PATH."
        )

    if args.tunnel:
        start_tunnel(args.port)
    application = create_vision_app(
        args.sam_model,
        args.depth_model,
        args.device,
    )
    uvicorn.run(application, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
