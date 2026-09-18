"""Tests for the dependency container's startup requirements."""

from pathlib import Path

import pytest

from app.presentation.dependencies import build_dependencies
from app.shared.config import (
    CatalogConfig,
    Config,
    DatabaseConfig,
    NutritionConfig,
    StorageConfig,
    VisionConfig,
)

SUPABASE_URL = "postgresql://user:secret@db.example.com:5432/postgres"
MODAL_URL = "https://example--ifne-vision-vision-api.modal.run"
STORAGE_URL = "https://project.supabase.co"
STORAGE_KEY = "service-role-key"


def local_config(tmp_path: Path) -> Config:
    """A configuration using only in-process providers."""
    return Config(
        database=DatabaseConfig(meal_repository="memory"),
        storage=StorageConfig(
            provider="local",
            base_path=str(tmp_path / "storage"),
        ),
        vision=VisionConfig(provider="mock"),
        nutrition=NutritionConfig(provider="manual"),
        catalog=CatalogConfig(provider="yaml"),
    )


def hosted_config(**overrides: object) -> Config:
    """The hosted stack, with any field overridable per test."""
    defaults: dict[str, object] = {
        "database": DatabaseConfig(url=SUPABASE_URL, meal_repository="sql"),
        "storage": StorageConfig(
            provider="supabase",
            supabase_url=STORAGE_URL,
            supabase_service_key=STORAGE_KEY,
        ),
        "vision": VisionConfig(provider="remote", remote_url=MODAL_URL),
        "nutrition": NutritionConfig(provider="sql"),
        "catalog": CatalogConfig(provider="sql"),
    }
    defaults.update(overrides)
    return Config(**defaults)  # type: ignore[arg-type]


class TestStartupRequirements:
    def test_defaults_require_supabase_and_modal(self) -> None:
        """The hosted stack is the default; nothing falls back locally."""
        with pytest.raises(ValueError) as error:
            build_dependencies(Config())

        message = str(error.value)
        assert "DATABASE_URL" in message
        assert "VISION_REMOTE_URL" in message

    def test_missing_database_url_is_reported(self) -> None:
        config = hosted_config(database=DatabaseConfig(meal_repository="sql"))

        with pytest.raises(ValueError, match="DATABASE_URL"):
            build_dependencies(config)

    def test_missing_remote_url_is_reported(self) -> None:
        config = hosted_config(vision=VisionConfig(provider="remote"))

        with pytest.raises(ValueError, match="VISION_REMOTE_URL"):
            build_dependencies(config)

    def test_unparseable_database_url_is_reported(self) -> None:
        """A placeholder or unencoded password fails here, not later."""
        config = hosted_config(
            database=DatabaseConfig(url="...", meal_repository="sql")
        )

        with pytest.raises(ValueError, match="not a connection string"):
            build_dependencies(config)

    def test_missing_storage_settings_are_reported(self) -> None:
        config = hosted_config(storage=StorageConfig(provider="supabase"))

        with pytest.raises(ValueError, match="SUPABASE_SERVICE_KEY"):
            build_dependencies(config)

    def test_sam3_without_model_paths_is_reported(self) -> None:
        config = hosted_config(vision=VisionConfig(provider="sam3"))

        with pytest.raises(ValueError, match="VISION_SAM_MODEL_PATH"):
            build_dependencies(config)

    def test_hosted_configuration_is_accepted(self) -> None:
        """A fully configured hosted stack assembles without complaints."""
        dependencies = build_dependencies(hosted_config())

        assert dependencies.config.database.url == SUPABASE_URL
        assert dependencies.config.vision.remote_url == MODAL_URL


class TestStaticImageMount:
    """Only the local provider serves images from disk."""

    @staticmethod
    def _mounted_paths(dependencies) -> list[str]:
        from app.presentation.api import create_app

        return [
            getattr(route, "path", "")
            for route in create_app(dependencies).routes
        ]

    def test_local_storage_creates_the_directory_and_mounts_it(
        self,
        tmp_path: Path,
    ) -> None:
        deps = build_dependencies(local_config(tmp_path))

        paths = self._mounted_paths(deps)

        assert "/api/v1/images" in paths
        assert (tmp_path / "storage").is_dir()

    def test_hosted_storage_touches_no_directory(
        self,
        tmp_path: Path,
    ) -> None:
        """A read-only container must not be asked to create a directory."""
        storage_path = tmp_path / "storage"
        config = hosted_config(
            storage=StorageConfig(
                provider="supabase",
                base_path=str(storage_path),
                supabase_url=STORAGE_URL,
                supabase_service_key=STORAGE_KEY,
            )
        )

        paths = self._mounted_paths(build_dependencies(config))

        assert "/api/v1/images" not in paths
        assert not storage_path.exists()


class TestLocalProviders:
    def test_explicit_local_providers_need_no_hosted_services(
        self,
        tmp_path: Path,
    ) -> None:
        """The alternative providers stay usable when chosen explicitly.

        Provider independence is an architectural constraint; the hosted
        stack is only the default, not the only option.
        """
        dependencies = build_dependencies(local_config(tmp_path))

        assert dependencies.config.database.url == ""
        assert dependencies.config.vision.provider == "mock"
        assert dependencies.search_foods is not None
        assert dependencies.list_meals is not None
