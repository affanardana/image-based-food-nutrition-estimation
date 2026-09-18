"""Database engine construction for SQL-backed providers."""

from sqlalchemy import Engine, create_engine

PSYCOPG_DRIVER = "postgresql+psycopg"


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for the given URL.

    Postgres URLs (Supabase and most hosts hand out ``postgresql://``)
    are routed to the psycopg 3 driver this project ships; without the
    explicit dialect SQLAlchemy would look for psycopg2.

    ``pool_pre_ping`` keeps pooled connections usable across the idle
    disconnects typical of hosted Postgres. Server-side prepared
    statements are disabled because Supabase's transaction pooler
    (pgbouncer) does not support them.
    """
    url = database_url
    connect_args: dict[str, object] = {}
    if url.startswith(("postgresql://", "postgres://")):
        _, _, remainder = url.partition("://")
        url = f"{PSYCOPG_DRIVER}://{remainder}"
        connect_args["prepare_threshold"] = None
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)
