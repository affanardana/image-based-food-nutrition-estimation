"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.presentation.dependencies import Dependencies, build_dependencies
from app.presentation.errors import register_error_handlers
from app.presentation.routers import foods, health, meals


def create_app(dependencies: Dependencies | None = None) -> FastAPI:
    """Create the FastAPI application with all routers and handlers."""
    deps = dependencies if dependencies is not None else build_dependencies()

    Path(deps.config.storage.base_path).mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="I-FNE API",
        version="0.2.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )
    app.state.dependencies = deps

    cors_origins = [
        origin.strip()
        for origin in deps.config.app.cors_origins.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(meals.router, prefix="/api/v1")
    app.include_router(foods.router, prefix="/api/v1")
    app.mount(
        "/api/v1/images",
        StaticFiles(directory=deps.config.storage.base_path),
        name="images",
    )
    register_error_handlers(app)
    return app
