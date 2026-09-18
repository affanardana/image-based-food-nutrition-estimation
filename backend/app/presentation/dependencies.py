"""Dependency container — wires providers and use cases for the API."""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from fastapi import Request
from sqlalchemy import Engine, make_url
from sqlalchemy.exc import ArgumentError

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
from app.domain.entities.segment import Segment, SegmentSuggestion
from app.domain.entities.vision_class import VisionClass
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog
from app.domain.interfaces.meal_repository import MealRepository
from app.domain.interfaces.nutrition_provider import NutritionProvider
from app.domain.interfaces.storage_provider import StorageProvider
from app.domain.interfaces.vision_provider import VisionProvider
from app.domain.values.bounding_box import BoundingBox
from app.domain.values.confidence_score import ConfidenceScore
from app.infrastructure.catalog.sql_canonical_food_catalog import (
    SqlCanonicalFoodCatalog,
)
from app.infrastructure.catalog.yaml_canonical_food_catalog import (
    YamlCanonicalFoodCatalog,
)
from app.infrastructure.nutrition.manual_nutrition_provider import (
    ManualNutritionProvider,
)
from app.infrastructure.nutrition.sql_nutrition_provider import (
    SqlNutritionProvider,
)
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.in_memory_meal_repository import (
    InMemoryMealRepository,
)
from app.infrastructure.persistence.sql_meal_repository import (
    SqlMealRepository,
)
from app.infrastructure.storage.local_storage_provider import (
    LocalStorageProvider,
)
from app.infrastructure.storage.supabase_storage_provider import (
    SupabaseStorageProvider,
)
from app.infrastructure.vision.depth import YOLODepthEstimator
from app.infrastructure.vision.mock_segmentation_provider import (
    MockSegmentationProvider,
)
from app.infrastructure.vision.remote_vision_provider import (
    RemoteVisionProvider,
)
from app.infrastructure.vision.sam3_segmentation_provider import (
    SAM3SegmentationProvider,
)
from app.shared.config import Config

BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Dependencies:
    """All use cases and configuration needed by the API layer."""

    segment_meal: SegmentMealUseCase
    label_segments: LabelSegmentsUseCase
    update_meal: UpdateMealUseCase
    get_meal: GetMealUseCase
    list_meals: ListMealsUseCase
    discard_segments: DiscardSegmentsUseCase
    delete_meal: DeleteMealUseCase
    search_foods: SearchFoodsUseCase
    config: Config


def build_dependencies(config: Config | None = None) -> Dependencies:
    """Assemble production dependencies from configuration.

    Raises:
        ValueError: If a selected provider is missing its configuration.
    """
    config = config if config is not None else Config.from_env()
    _validate_config(config)

    engine = _build_engine(config)
    catalog = _build_catalog(config, engine)
    nutrition_provider = _build_nutrition_provider(config, engine)
    storage_provider = _build_storage_provider(config)
    vision_provider = _build_vision_provider(config, catalog, storage_provider)
    repository = _build_meal_repository(config, engine)

    nutrition_resolver = NutritionResolver(nutrition_provider)
    measurement_estimator = MeasurementEstimator()

    return Dependencies(
        segment_meal=SegmentMealUseCase(
            vision_provider,
            repository,
            storage_provider,
        ),
        label_segments=LabelSegmentsUseCase(
            repository,
            catalog,
            nutrition_resolver,
            measurement_estimator,
        ),
        update_meal=UpdateMealUseCase(
            repository,
            nutrition_resolver,
            catalog,
        ),
        get_meal=GetMealUseCase(repository),
        list_meals=ListMealsUseCase(repository),
        discard_segments=DiscardSegmentsUseCase(
            repository,
            storage_provider,
            nutrition_resolver,
            measurement_estimator,
        ),
        delete_meal=DeleteMealUseCase(repository, storage_provider),
        search_foods=SearchFoodsUseCase(catalog),
        config=config,
    )


def get_dependencies(request: Request) -> Dependencies:
    """FastAPI dependency accessor."""
    return cast(Dependencies, request.app.state.dependencies)


def _uses_sql(config: Config) -> bool:
    """True when any provider reads from the SQL database."""
    return (
        config.catalog.provider == "sql"
        or config.nutrition.provider == "sql"
        or config.database.meal_repository == "sql"
    )


def _is_parseable_url(database_url: str) -> bool:
    """True when SQLAlchemy can parse the configured database URL.

    Catches the common deployment mistake of a placeholder or an
    unencoded password, which would otherwise fail later with SQLAlchemy's
    own "Could not parse SQLAlchemy URL" message.
    """
    try:
        make_url(database_url)
    except ArgumentError:
        return False
    return True


def _validate_config(config: Config) -> None:
    """Fail fast when a selected provider has no configuration.

    The hosted stack is the default, so a missing Supabase URL or Modal
    endpoint stops the application at startup with an actionable message,
    rather than appearing as an error on the first request or — worse —
    silently running against a local database.

    Raises:
        ValueError: Listing every missing setting at once.
    """
    missing: list[str] = []
    if _uses_sql(config) and not config.database.url:
        missing.append(
            "DATABASE_URL — the Supabase Postgres connection string, "
            "required by CATALOG_PROVIDER / NUTRITION_PROVIDER / "
            "MEAL_REPOSITORY = sql"
        )
    elif _uses_sql(config) and not _is_parseable_url(config.database.url):
        missing.append(
            "DATABASE_URL is not a connection string SQLAlchemy can parse — "
            "it should look like postgresql://postgres.<ref>:<password>"
            "@aws-0-<region>.pooler.supabase.com:5432/postgres "
            "(percent-encode @ : / # ? if they appear in the password)"
        )
    if config.storage.provider == "supabase" and (
        not config.storage.supabase_url
        or not config.storage.supabase_service_key
    ):
        missing.append(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY — required by "
            "STORAGE_PROVIDER=supabase (the bucket is public-read, so "
            "these are read from the environment only)"
        )
    if config.vision.provider == "remote" and not config.vision.remote_url:
        missing.append(
            "VISION_REMOTE_URL — the Modal inference endpoint, "
            "required by VISION_PROVIDER=remote"
        )
    if config.vision.provider == "sam3" and (
        not config.vision.sam_model_path
        or not config.vision.depth_model_path
    ):
        missing.append(
            "VISION_SAM_MODEL_PATH and VISION_DEPTH_MODEL_PATH — "
            "required by VISION_PROVIDER=sam3"
        )
    if missing:
        details = "\n".join(f"  - {item}" for item in missing)
        raise ValueError(f"Missing required configuration:\n{details}")


def _build_engine(config: Config) -> Engine | None:
    """Create a database engine when any SQL-backed provider is selected."""
    if _uses_sql(config):
        return create_database_engine(config.database.url)
    return None


def _build_storage_provider(config: Config) -> StorageProvider:
    """Select the storage provider based on configuration."""
    if config.storage.provider == "supabase":
        return SupabaseStorageProvider(
            base_url=config.storage.supabase_url,
            service_key=config.storage.supabase_service_key,
            bucket=config.storage.supabase_bucket,
        )
    return LocalStorageProvider(config.storage.base_path)


def _build_meal_repository(
    config: Config,
    engine: Engine | None,
) -> MealRepository:
    """Select the meal repository based on configuration."""
    if config.database.meal_repository == "sql":
        if engine is None:
            raise ValueError(
                "A database engine is required for MEAL_REPOSITORY=sql"
            )
        return SqlMealRepository(engine)
    return InMemoryMealRepository()


def _build_catalog(config: Config, engine: Engine | None) -> CanonicalFoodCatalog:
    """Select the canonical food catalog based on configuration."""
    if config.catalog.provider == "sql":
        if engine is None:
            raise ValueError("A database engine is required for CATALOG_PROVIDER=sql")
        return SqlCanonicalFoodCatalog(engine)
    return YamlCanonicalFoodCatalog(
        str(BASE_DIR / "mappings" / "canonical_foods.yaml")
    )


def _build_nutrition_provider(
    config: Config,
    engine: Engine | None,
) -> NutritionProvider:
    """Select the nutrition provider based on configuration."""
    if config.nutrition.provider == "sql":
        if engine is None:
            raise ValueError(
                "A database engine is required for NUTRITION_PROVIDER=sql"
            )
        return SqlNutritionProvider(engine, source=config.nutrition.source)
    return ManualNutritionProvider(
        str(BASE_DIR / "data" / "nutrition_database.yaml")
    )


def _build_vision_provider(
    config: Config,
    catalog: CanonicalFoodCatalog,
    storage_provider: StorageProvider,
) -> VisionProvider:
    """Select the vision provider based on configuration."""
    if config.vision.provider == "sam3":
        depth_estimator = YOLODepthEstimator(
            config.vision.depth_model_path,
            device=config.vision.device,
        )
        return SAM3SegmentationProvider(
            sam_model_path=config.vision.sam_model_path,
            depth_estimator=depth_estimator,
            storage_provider=storage_provider,
            catalog=catalog,
            device=config.vision.device,
        )
    if config.vision.provider == "remote":
        return RemoteVisionProvider(
            base_url=config.vision.remote_url,
            storage_provider=storage_provider,
            catalog=catalog,
        )
    return MockSegmentationProvider(_demo_segments())


def _demo_segments() -> list[Segment]:
    """Fixed demo segments produced by the mock provider.

    Simulates two sate skewers and one lontong piece with the mask
    statistics the real SAM + depth pipeline would produce.
    """
    return [
        Segment(
            segment_id="seg_001",
            crop_image_ref="/api/v1/images/crops/seg_001.jpg",
            mask_area_px=45_000.0,
            normalized_area=0.9,
            bounding_box=BoundingBox(x=10, y=20, width=250, height=200),
            max_normalized_depth=0.6,
            provider_name="mock_segmentation",
            provider_version="0.1.0",
            suggestion=SegmentSuggestion(
                vision_class=VisionClass(label="sate"),
                confidence=ConfidenceScore(value=0.94),
            ),
        ),
        Segment(
            segment_id="seg_002",
            crop_image_ref="/api/v1/images/crops/seg_002.jpg",
            mask_area_px=38_000.0,
            normalized_area=0.85,
            bounding_box=BoundingBox(x=280, y=30, width=220, height=180),
            max_normalized_depth=0.55,
            provider_name="mock_segmentation",
            provider_version="0.1.0",
            suggestion=SegmentSuggestion(
                vision_class=VisionClass(label="sate"),
                confidence=ConfidenceScore(value=0.88),
            ),
        ),
        Segment(
            segment_id="seg_003",
            crop_image_ref="/api/v1/images/crops/seg_003.jpg",
            mask_area_px=52_000.0,
            normalized_area=0.8,
            bounding_box=BoundingBox(x=520, y=10, width=260, height=210),
            max_normalized_depth=0.7,
            provider_name="mock_segmentation",
            provider_version="0.1.0",
            suggestion=SegmentSuggestion(
                vision_class=VisionClass(label="lontong"),
                confidence=ConfidenceScore(value=0.91),
            ),
        ),
    ]
