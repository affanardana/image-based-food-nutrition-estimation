"""Shared helpers for infrastructure tests."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.persistence.schema import metadata


def make_sqlite_engine() -> Engine:
    """Create an in-memory SQLite engine with the food schema applied.

    StaticPool keeps every connection on the same in-memory database so
    tests can write fixtures and query them through the providers.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    return engine
