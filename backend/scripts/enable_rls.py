"""Enable Row-Level Security on the application's tables.

Supabase exposes an auto-generated REST API over the ``public`` schema,
reachable with the project's anon key — which is public by design, since
it ships inside client applications. With RLS disabled, every table in
that schema can be read, edited and deleted by anyone holding the project
URL and that key. Supabase reports this as ``rls_disabled_in_public``.

This enables RLS on those tables and defines no policies, which denies
access by default. The backend is unaffected: it connects as the table
owner, and a table owner bypasses RLS.

    uv run python scripts/enable_rls.py
    uv run python scripts/enable_rls.py --dry-run

The database URL defaults to $DATABASE_URL.

Re-run it after ``create_schema.py --drop-meal-tables``: a table that is
dropped and recreated starts again with RLS disabled.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import ArgumentError

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.persistence.database import create_database_engine

PUBLIC_SCHEMA = "public"

_TABLES_QUERY = text(
    """
    SELECT tablename, tableowner, rowsecurity
    FROM pg_tables
    WHERE schemaname = :schema
    ORDER BY tablename
    """
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="SQLAlchemy database URL (default: DATABASE_URL)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the current state without changing anything",
    )
    return parser.parse_args()


def quote_identifier(name: str) -> str:
    """Quote a SQL identifier, escaping any embedded quotes."""
    return '"' + name.replace('"', '""') + '"'


def fetch_tables(connection: Connection) -> list[dict[str, object]]:
    """Describe every table in the schema: name, owner, RLS state."""
    rows = connection.execute(
        _TABLES_QUERY,
        {"schema": PUBLIC_SCHEMA},
    ).mappings()
    return [dict(row) for row in rows]


def describe(
    role: str,
    tables: list[dict[str, object]],
    unprotected: list[str],
) -> None:
    """Report the current state and any risk RLS would introduce."""
    print(f"Connected as: {role}")
    print(
        f"Tables in '{PUBLIC_SCHEMA}': {len(tables)} "
        f"({len(tables) - len(unprotected)} with RLS, "
        f"{len(unprotected)} without)"
    )
    if unprotected:
        print(f"Without RLS: {', '.join(unprotected)}")

    # A table owner bypasses RLS, so the backend keeps its access. A role
    # that does not own the tables would be locked out once RLS is on —
    # which is worth knowing before it happens, not after.
    not_owned = [
        str(table["tablename"])
        for table in tables
        if table["tableowner"] != role
    ]
    if not_owned:
        print(
            "\nWARNING: these tables are owned by a different role than the "
            "one connecting now, so RLS would also restrict this connection: "
            f"{', '.join(not_owned)}"
        )


def enable_rls(engine: Engine, dry_run: bool) -> int:
    """Enable RLS on every table in the schema that lacks it."""
    with engine.begin() as connection:
        role = str(connection.execute(text("SELECT current_user")).scalar_one())
        tables = fetch_tables(connection)
        if not tables:
            print(f"No tables found in '{PUBLIC_SCHEMA}'.")
            return 0

        unprotected = [
            str(table["tablename"])
            for table in tables
            if not table["rowsecurity"]
        ]
        describe(role, tables, unprotected)

        if not unprotected:
            print("\nEvery table already has RLS enabled. Nothing to do.")
            return 0
        if dry_run:
            print("\nDry run: nothing changed.")
            return 0

        for name in unprotected:
            connection.execute(
                text(
                    f"ALTER TABLE {PUBLIC_SCHEMA}.{quote_identifier(name)} "
                    "ENABLE ROW LEVEL SECURITY"
                )
            )

        remaining = [
            str(table["tablename"])
            for table in fetch_tables(connection)
            if not table["rowsecurity"]
        ]

    print(f"\nEnabled RLS on {len(unprotected)} tables.")
    if remaining:
        print(f"Still without RLS: {', '.join(remaining)}")
        return 1
    print("Verified: every table in the schema now has RLS enabled.")
    return 0


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit(
            "Missing database URL. Pass --database-url or set DATABASE_URL."
        )
    try:
        engine = create_database_engine(args.database_url)
    except ArgumentError as exc:
        # A host, a password, or a fragment pasted on its own is an easy
        # mistake to make and produces an opaque SQLAlchemy error.
        raise SystemExit(
            "That is not a complete database URL.\n\n"
            "The whole connection string is needed, in this shape:\n"
            "  postgresql://postgres.<project-ref>:<password>"
            "@aws-0-<region>.pooler.supabase.com:5432/postgres\n\n"
            "Copy it from Supabase: Project Settings, Database, "
            "Connection string, Session pooler."
        ) from exc
    if engine.dialect.name != "postgresql":
        raise SystemExit(
            "Row-Level Security is a PostgreSQL feature; this database is "
            f"'{engine.dialect.name}'. Nothing to do."
        )
    return enable_rls(engine, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
