"""Move locally stored meal images and crops into hosted storage.

Meals analyzed while the backend used local storage keep filesystem
references in the database (``storage/meal_....jpeg``). On a host with an
ephemeral filesystem those references point at nothing, so the history
thumbnails and the label screen show broken images. This script uploads
the files that are still on this machine and rewrites the stored
references to public URLs.

    uv run python scripts/migrate_meal_images.py            # report only
    uv run python scripts/migrate_meal_images.py --apply    # upload + rewrite

Requires DATABASE_URL, SUPABASE_URL and SUPABASE_SERVICE_KEY, plus the
original files under ``--storage-path``. Meals whose files are gone are
reported and left untouched: nothing is deleted, and the run is safe to
repeat — rewritten references are URLs, so they are never selected again.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import Connection, Engine, select, update
from sqlalchemy.engine import Row

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.schema import meals, segments
from app.infrastructure.storage.supabase_storage_provider import (
    SupabaseStorageProvider,
)
from app.shared.config import Config

BASE_DIR = Path(__file__).resolve().parents[1]

HOSTED_PREFIXES = ("http://", "https://")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="SQLAlchemy database URL (default: DATABASE_URL)",
    )
    parser.add_argument(
        "--storage-path",
        default=str(BASE_DIR / "storage"),
        help="Directory holding the original files",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Upload and rewrite (without it, nothing is changed)",
    )
    return parser.parse_args()


def is_hosted(reference: str) -> bool:
    """Whether a stored reference is already a URL."""
    return reference.startswith(HOSTED_PREFIXES)


def resolve_local_file(reference: str, storage_dir: Path) -> Path | None:
    """Find the file behind a stored reference, if it is still here.

    The reference may be relative (``storage/meal_1.jpeg``), absolute, or
    carry a different base than the current configuration, so the name is
    tried against the storage directory as well.
    """
    for candidate in (
        storage_dir / Path(reference).name,
        Path(reference),
        BASE_DIR / reference,
    ):
        if candidate.is_file():
            return candidate
    return None


def object_key(path: Path, storage_dir: Path) -> str:
    """The bucket key for a file, mirroring how the app names objects."""
    try:
        return path.relative_to(storage_dir).as_posix()
    except ValueError:
        return path.name


def select_local_meal_rows(
    connection: Connection,
) -> list[Row[tuple[str, str]]]:
    """Meals whose image reference is not a URL."""
    rows = connection.execute(
        select(meals.c.meal_id, meals.c.image_path).order_by(meals.c.created_at)
    ).all()
    return [row for row in rows if not is_hosted(row.image_path)]


def select_local_crop_rows(
    connection: Connection,
    meal_ids: list[str],
) -> list[Row[tuple[str, str, str]]]:
    """Crops of the given meals whose reference is not a URL."""
    if not meal_ids:
        return []
    rows = connection.execute(
        select(
            segments.c.meal_id,
            segments.c.segment_id,
            segments.c.crop_image_ref,
        ).where(segments.c.meal_id.in_(meal_ids))
    ).all()
    return [row for row in rows if not is_hosted(row.crop_image_ref)]


def upload(
    storage: SupabaseStorageProvider,
    reference: str,
    storage_dir: Path,
) -> str | None:
    """Upload one local file and return its public URL."""
    path = resolve_local_file(reference, storage_dir)
    if path is None:
        return None
    return storage.store(str(path), object_key(path, storage_dir))


def report(engine: Engine, storage_dir: Path) -> None:
    """Describe what a migration would do, without changing anything."""
    with engine.connect() as connection:
        meal_rows = select_local_meal_rows(connection)
        crops = select_local_crop_rows(
            connection,
            [row.meal_id for row in meal_rows],
        )

    print(f"Storage directory: {storage_dir}")
    print(f"Meals with a filesystem reference: {len(meal_rows)}")
    print(f"Crops with a filesystem reference: {len(crops)}")
    if meal_rows:
        print("\nStored meal references (as they are in the database):")
        for row in meal_rows:
            found = resolve_local_file(row.image_path, storage_dir)
            state = f"found -> {found}" if found else "FILE MISSING"
            print(f"  {row.meal_id}: {row.image_path!r}  [{state}]")
    missing_crops = [
        row
        for row in crops
        if resolve_local_file(row.crop_image_ref, storage_dir) is None
    ]
    print(f"\nCrops whose file is missing: {len(missing_crops)}")
    print("\nDry run: nothing uploaded or changed.")


def migrate(engine: Engine, storage: SupabaseStorageProvider, storage_dir: Path) -> int:
    """Upload the surviving files and rewrite the references."""
    with engine.connect() as connection:
        meal_rows = select_local_meal_rows(connection)
        crops = select_local_crop_rows(
            connection,
            [row.meal_id for row in meal_rows],
        )

    uploaded_meals: list[tuple[str, str]] = []
    missing_meals: list[str] = []
    for row in meal_rows:
        url = upload(storage, row.image_path, storage_dir)
        if url is None:
            missing_meals.append(row.meal_id)
            continue
        uploaded_meals.append((row.meal_id, url))
        print(f"meal {row.meal_id}: uploaded -> {url}")

    uploaded_crops: list[tuple[str, str, str]] = []
    for crop in crops:
        url = upload(storage, crop.crop_image_ref, storage_dir)
        if url is None:
            continue
        uploaded_crops.append((crop.meal_id, crop.segment_id, url))
    print(f"crops uploaded: {len(uploaded_crops)}")

    # One transaction: either every rewritten reference lands, or none
    # does — a half-rewritten meal would mix working and dead images.
    with engine.begin() as connection:
        for meal_id, url in uploaded_meals:
            connection.execute(
                update(meals)
                .where(meals.c.meal_id == meal_id)
                .values(image_path=url)
            )
        for meal_id, segment_id, url in uploaded_crops:
            connection.execute(
                update(segments)
                .where(
                    segments.c.meal_id == meal_id,
                    segments.c.segment_id == segment_id,
                )
                .values(crop_image_ref=url)
            )

    print(f"\nRewritten: {len(uploaded_meals)} meals, {len(uploaded_crops)} crops")
    if missing_meals:
        print(
            f"Skipped {len(missing_meals)} meals whose files are gone "
            f"(their images cannot be recovered): {', '.join(missing_meals)}"
        )
    return 0 if not missing_meals else 1


def main() -> int:
    args = parse_args()
    storage_dir = Path(args.storage_path)
    settings = Config.from_env()

    if not args.database_url:
        raise SystemExit(
            "Missing database URL. Pass --database-url or set DATABASE_URL."
        )
    if not args.apply:
        # Reporting needs only the database: no credentials, no writes.
        report(create_database_engine(args.database_url), storage_dir)
        return 0
    if not settings.storage.supabase_url or not settings.storage.supabase_service_key:
        raise SystemExit(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in the environment."
        )

    return migrate(
        create_database_engine(args.database_url),
        SupabaseStorageProvider(
            base_url=settings.storage.supabase_url,
            service_key=settings.storage.supabase_service_key,
            bucket=settings.storage.supabase_bucket,
        ),
        storage_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
