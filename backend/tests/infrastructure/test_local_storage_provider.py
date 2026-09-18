"""Tests for LocalStorageProvider."""

from pathlib import Path

from app.infrastructure.storage.local_storage_provider import (
    LocalStorageProvider,
)


class TestLocalStorageProvider:
    def test_store_retrieve_roundtrip(self, tmp_path: Path) -> None:
        provider = LocalStorageProvider(str(tmp_path / "storage"))
        source = tmp_path / "upload.jpg"
        source.write_bytes(b"fake-image-bytes")

        stored_path = provider.store(str(source), "meal_001.jpg")

        assert Path(stored_path).exists()
        assert provider.retrieve(stored_path) == b"fake-image-bytes"

    def test_store_creates_base_directory(self, tmp_path: Path) -> None:
        provider = LocalStorageProvider(str(tmp_path / "nested" / "storage"))
        source = tmp_path / "upload.jpg"
        source.write_bytes(b"data")

        stored_path = provider.store(str(source), "img.jpg")

        assert Path(stored_path).exists()

    def test_store_creates_nested_destination_directories(
        self, tmp_path: Path
    ) -> None:
        provider = LocalStorageProvider(str(tmp_path / "storage"))
        source = tmp_path / "upload.jpg"
        source.write_bytes(b"data")

        stored_path = provider.store(str(source), "crops/seg_001.jpg")

        assert Path(stored_path).exists()
        assert Path(stored_path) == tmp_path / "storage" / "crops" / "seg_001.jpg"

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        provider = LocalStorageProvider(str(tmp_path))
        source = tmp_path / "upload.jpg"
        source.write_bytes(b"data")
        stored_path = provider.store(str(source), "img.jpg")

        provider.delete(stored_path)

        assert not Path(stored_path).exists()

    def test_delete_missing_file_is_noop(self, tmp_path: Path) -> None:
        provider = LocalStorageProvider(str(tmp_path))

        # Should not raise
        provider.delete(str(tmp_path / "does_not_exist.jpg"))
