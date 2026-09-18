"""Uvicorn entry point.

Run with: uv run uvicorn app.main:app --reload
"""

from app.presentation.api import create_app

app = create_app()
