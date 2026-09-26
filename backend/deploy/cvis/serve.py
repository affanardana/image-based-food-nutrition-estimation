"""ASGI entry point for the vision service on a plain host.

Modal wraps ``create_vision_app`` in an ``asgi_app``; on a server it is
uvicorn that needs a module-level application object, so this is the
equivalent wrapper:

    uvicorn serve:app --host 0.0.0.0 --port 8000
"""

import os

from inference.vision_service import create_vision_app

app = create_vision_app(
    sam_model_path=os.environ["SAM_MODEL_PATH"],
    depth_model_path=os.environ["DEPTH_MODEL_PATH"],
    device=os.getenv("VISION_DEVICE", "cpu"),
)
