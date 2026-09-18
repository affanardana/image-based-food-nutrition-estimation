"""Shared helpers for presentation tests."""

import struct
import zlib
from pathlib import Path

from fastapi import FastAPI

from app.application.services.measurement_estimator import MeasurementEstimator
from app.application.services.nutrition_resolver import NutritionResolver
from app.application.use_cases.delete_meal import DeleteMealUseCase
from app.application.use_cases.discard_segments import DiscardSegmentsUseCase
from app.application.use_cases.get_meal import GetMealUseCase
from app.application.use_cases.label_segments import LabelSegmentsUseCase
from app.application.use_cases.list_meals import ListMealsUseCase
from app.application.use_cases.search_foods import SearchFoodsUseCase
from app.application.use_cases.segment_meal import SegmentMealUseCase
from app.application.use_cases.update_meal import UpdateMealUseCase
from app.domain.entities.canonical_food import CanonicalFood
from app.domain.values.nutrition_values import NutritionProfile
from app.presentation.api import create_app
from app.presentation.dependencies import Dependencies
from app.shared.config import Config, StorageConfig
from tests.application.fakes import (
    FakeCatalog,
    FakeMealRepository,
    FakeNutritionProvider,
    FakeStorageProvider,
    FakeVisionProvider,
)
from tests.helpers import make_segment

SATE = CanonicalFood(id="sate", name="Sate", typical_weight_g=100.0)
LONTONG = CanonicalFood(id="lontong", name="Lontong", typical_weight_g=100.0)
BURGER = CanonicalFood(id="burger", name="Burger", typical_weight_g=200.0)

PROFILES = {
    "sate": NutritionProfile(calories_kcal=218.0, protein_g=24.5),
    "lontong": NutritionProfile(calories_kcal=130.0, protein_g=2.2),
    "burger": NutritionProfile(calories_kcal=250.0, protein_g=13.0),
}


def make_test_dependencies(
    tmp_path: Path,
    max_upload_size_mb: int = 10,
) -> tuple[Dependencies, FakeMealRepository, FakeStorageProvider]:
    """Assemble API dependencies with fakes and in-memory providers."""
    repo = FakeMealRepository()
    storage = FakeStorageProvider(str(tmp_path / "storage"))
    catalog = FakeCatalog(
        foods=[SATE, LONTONG, BURGER],
        vision_mapping={"cheeseburger": "burger"},
    )
    nutrition = FakeNutritionProvider(PROFILES)
    vision = FakeVisionProvider(
        [
            make_segment("seg_001", suggestion_label="sate"),
            make_segment("seg_002", suggestion_label="lontong"),
        ]
    )
    resolver = NutritionResolver(nutrition)
    estimator = MeasurementEstimator()

    deps = Dependencies(
        segment_meal=SegmentMealUseCase(vision, repo, storage),
        label_segments=LabelSegmentsUseCase(repo, catalog, resolver, estimator),
        update_meal=UpdateMealUseCase(repo, resolver, catalog),
        get_meal=GetMealUseCase(repo),
        list_meals=ListMealsUseCase(repo),
        discard_segments=DiscardSegmentsUseCase(
            repo,
            storage,
            resolver,
            estimator,
        ),
        delete_meal=DeleteMealUseCase(repo, storage),
        search_foods=SearchFoodsUseCase(catalog),
        config=Config(
            storage=StorageConfig(
                base_path=str(tmp_path / "storage"),
                max_upload_size_mb=max_upload_size_mb,
            )
        ),
    )
    return deps, repo, storage


def make_test_app(tmp_path: Path) -> FastAPI:
    """Create a FastAPI app wired with test dependencies."""
    deps, _, _ = make_test_dependencies(tmp_path)
    return create_app(deps)


def make_png_bytes(width: int = 100, height: int = 50) -> bytes:
    """Build a minimal valid PNG file with the given IHDR dimensions."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = (
        struct.pack(">I", 13)
        + b"IHDR"
        + ihdr
        + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    )
    return b"\x89PNG\r\n\x1a\n" + chunk


def make_jpeg_bytes(width: int = 80, height: int = 40) -> bytes:
    """Build a minimal JPEG with a start-of-frame marker carrying dimensions."""
    payload = (
        b"\x08"  # precision
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x01"  # one component
    )
    sof0 = b"\xff\xc0" + (len(payload) + 2).to_bytes(2, "big") + payload
    return b"\xff\xd8" + sof0 + b"\xff\xd9"
