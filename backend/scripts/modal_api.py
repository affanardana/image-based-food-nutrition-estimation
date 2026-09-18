"""Serve the backend API on Modal.

The application needs no server of its own: Modal starts a container on
demand and stops it after the scaledown window. Nothing is persisted on
that host — meals live in Supabase Postgres and images in Supabase
Storage — so containers coming and going is harmless.

Deploy from the backend directory (`add_local_python_source("app")`
needs it as the working directory):

    uv run modal secret create ifne-api \\
        DATABASE_URL="postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres" \\
        VISION_REMOTE_URL="https://<workspace>--ifne-vision-vision-api.modal.run" \\
        SUPABASE_URL="https://<ref>.supabase.co" \\
        SUPABASE_SERVICE_KEY="<service-role key>" \\
        CORS_ORIGINS="https://<frontend>.vercel.app"

    uv run modal deploy scripts/modal_api.py

The URL it prints is the frontend's `VITE_API_BASE_URL`. Secrets are read
when a container starts, so after changing one, deploy again (or wait for
the container to scale down) for the new values to take effect.

Check the deployment without going through the browser (this also builds
the image, which a deploy does not wait for):

    uv run modal run scripts/modal_api.py::verify_api
"""

from typing import TYPE_CHECKING

import modal

if TYPE_CHECKING:
    from fastapi import FastAPI

APP_NAME = "ifne-api"
SECRET_NAME = "ifne-api"

# Generous: an analyze request waits on the vision service, which may
# itself be starting up.
REQUEST_TIMEOUT_SECONDS = 300
SCALEDOWN_WINDOW_SECONDS = 300

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.12")
    # Dependencies come from the project file so they cannot drift from
    # what is developed and tested against.
    .pip_install_from_pyproject("pyproject.toml")
    .add_local_python_source("app")
)

secrets = modal.Secret.from_name(SECRET_NAME)


@app.function(
    image=image,
    secrets=[secrets],
    timeout=REQUEST_TIMEOUT_SECONDS,
    scaledown_window=SCALEDOWN_WINDOW_SECONDS,
)
@modal.asgi_app()
def api() -> "FastAPI":
    """Serve the backend API."""
    from app.presentation.api import create_app

    return create_app()


@app.function(image=image, secrets=[secrets], timeout=600)
def verify_api() -> None:
    """Build the image and check everything the API depends on.

    Forces the image build into view (a deploy does not wait for it) and
    then exercises the database and the storage bucket, so a
    misconfiguration is found here instead of through the browser:

        uv run modal run scripts/modal_api.py::verify_api
    """
    import tempfile
    from pathlib import Path
    from urllib import request as urlrequest

    from sqlalchemy import func, select

    from app.infrastructure.persistence.database import create_database_engine
    from app.infrastructure.persistence.schema import canonical_foods
    from app.infrastructure.storage.supabase_storage_provider import (
        SupabaseStorageProvider,
    )
    from app.presentation.api import create_app
    from app.shared.config import Config

    # Settings first: if a secret is malformed, the app cannot even be
    # built, and these lines are what identify the bad value.
    settings = Config.from_env()
    print(f"vision  : {settings.vision.provider} -> {settings.vision.remote_url}")
    print(f"storage : {settings.storage.provider} -> {settings.storage.supabase_url}")
    print(f"cors    : {settings.app.cors_origins}")
    # Host only: the connection string carries the database password.
    print(f"database: {settings.database.url.split('@')[-1]}")

    application = create_app()
    paths = sorted(
        str(getattr(route, "path", ""))
        for route in application.routes
        if str(getattr(route, "path", "")).startswith("/api/")
    )
    print(f"Application built; routes: {', '.join(paths)}")

    engine = create_database_engine(settings.database.url)
    with engine.connect() as connection:
        foods = connection.execute(
            select(func.count()).select_from(canonical_foods)
        ).scalar_one()
    print(f"Database reachable: {foods} canonical foods")

    storage = SupabaseStorageProvider(
        settings.storage.supabase_url,
        settings.storage.supabase_service_key,
        settings.storage.supabase_bucket,
    )
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
        handle.write(b"ifne storage check")
        probe_path = handle.name
    reference = ""
    try:
        reference = storage.store(probe_path, "healthcheck/probe.txt")
        print(f"Storage writable: {reference}")
        with urlrequest.urlopen(reference, timeout=60) as response:
            body = response.read()
        print(
            "Storage publicly readable: "
            f"{body == b'ifne storage check'} (bucket must be public)"
        )
    finally:
        Path(probe_path).unlink(missing_ok=True)
        if reference:
            storage.delete(reference)

    print("All checks finished.")
