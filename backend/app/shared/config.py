"""Application configuration loaded from environment variables.

The defaults describe the hosted deployment: Supabase holds the food
data and meals, and Modal serves vision inference. Nothing falls back
to a local database or a mock model, so a missing setting fails at
startup instead of silently running against local state.

The local providers (mock vision, YAML catalog, manual nutrition,
in-memory meals) remain available — they are what the test suite uses —
but they must be selected explicitly.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    debug: bool = False
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


@dataclass(frozen=True)
class DatabaseConfig:
    """Database connection and persistence configuration."""

    url: str = ""  # required: the Supabase connection string
    meal_repository: str = "sql"  # memory | sql


@dataclass(frozen=True)
class StorageConfig:
    """Storage configuration for uploaded images and crops."""

    provider: str = "supabase"  # supabase | local
    base_path: str = "./storage"  # used by the local provider
    max_upload_size_mb: int = 10
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "ifne"


@dataclass(frozen=True)
class VisionConfig:
    """Vision provider configuration."""

    provider: str = "remote"  # remote | sam3 | mock
    sam_model_path: str = ""
    depth_model_path: str = ""
    remote_url: str = ""  # required when provider is remote
    device: str = "auto"


@dataclass(frozen=True)
class NutritionConfig:
    """Nutrition provider configuration."""

    provider: str = "sql"  # manual | sql
    source: str = "nutrition_csv"


@dataclass(frozen=True)
class CatalogConfig:
    """Canonical food catalog configuration."""

    provider: str = "sql"  # yaml | sql


@dataclass(frozen=True)
class Config:
    """Aggregated configuration for the entire application."""

    app: AppConfig = field(default_factory=AppConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    nutrition: NutritionConfig = field(default_factory=NutritionConfig)
    catalog: CatalogConfig = field(default_factory=CatalogConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Build configuration from environment variables."""
        return cls(
            app=AppConfig(
                debug=os.getenv("APP_DEBUG", "false").lower() == "true",
                environment=os.getenv("APP_ENV", "development"),
                cors_origins=os.getenv(
                    "CORS_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173",
                ),
            ),
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", ""),
                meal_repository=os.getenv("MEAL_REPOSITORY", "sql"),
            ),
            storage=StorageConfig(
                provider=os.getenv("STORAGE_PROVIDER", "supabase"),
                base_path=os.getenv("STORAGE_PATH", "./storage"),
                max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")),
                supabase_url=os.getenv("SUPABASE_URL", ""),
                supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
                supabase_bucket=os.getenv("SUPABASE_BUCKET", "ifne"),
            ),
            vision=VisionConfig(
                provider=os.getenv("VISION_PROVIDER", "remote"),
                sam_model_path=os.getenv("VISION_SAM_MODEL_PATH", ""),
                depth_model_path=os.getenv("VISION_DEPTH_MODEL_PATH", ""),
                remote_url=os.getenv("VISION_REMOTE_URL", ""),
                device=os.getenv("VISION_DEVICE", "auto"),
            ),
            nutrition=NutritionConfig(
                provider=os.getenv("NUTRITION_PROVIDER", "sql"),
                source=os.getenv("NUTRITION_SOURCE", "nutrition_csv"),
            ),
            catalog=CatalogConfig(
                provider=os.getenv("CATALOG_PROVIDER", "sql"),
            ),
        )
