"""Tests for SupabaseStorageProvider — with a stubbed HTTP transport."""

from pathlib import Path
from typing import Any

import pytest

from app.infrastructure.storage.supabase_storage_provider import (
    SupabaseStorageProvider,
)

BASE_URL = "https://project.supabase.co"
BUCKET = "ifne"


class StubStorageProvider(SupabaseStorageProvider):
    """Provider with the HTTP layer stubbed; records every call."""

    def __init__(self, response: Exception | None = None) -> None:
        super().__init__(BASE_URL, "service-key", BUCKET)
        self.calls: list[dict[str, Any]] = []
        self._response = response

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> bytes:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "data": data,
                "content_type": content_type,
                "extra_headers": extra_headers or {},
            }
        )
        if self._response is not None:
            raise self._response
        return b"downloaded-bytes"


def make_provider(response: Exception | None = None) -> StubStorageProvider:
    return StubStorageProvider(response)


class TestStore:
    def test_uploads_and_returns_the_public_url(self, tmp_path: Path) -> None:
        source = tmp_path / "meal.jpg"
        source.write_bytes(b"jpeg-bytes")
        provider = make_provider()

        reference = provider.store(str(source), "crops/meal_1_seg_001.jpg")

        assert reference == (
            f"{BASE_URL}/storage/v1/object/public/{BUCKET}/"
            "crops/meal_1_seg_001.jpg"
        )
        call = provider.calls[0]
        assert call["method"] == "POST"
        assert call["path"] == "/storage/v1/object/ifne/crops/meal_1_seg_001.jpg"
        assert call["data"] == b"jpeg-bytes"
        assert call["content_type"] == "image/jpeg"
        assert call["extra_headers"] == {"x-upsert": "true"}

    def test_png_content_type(self, tmp_path: Path) -> None:
        source = tmp_path / "crop.png"
        source.write_bytes(b"png-bytes")
        provider = make_provider()

        provider.store(str(source), "crops/crop.png")

        assert provider.calls[0]["content_type"] == "image/png"

    def test_upload_failure_raises_runtime_error(self, tmp_path: Path) -> None:
        source = tmp_path / "meal.jpg"
        source.write_bytes(b"jpeg-bytes")
        provider = make_provider(RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            provider.store(str(source), "meal.jpg")


class TestRetrieve:
    def test_accepts_a_public_url(self) -> None:
        provider = make_provider()
        public = (
            f"{BASE_URL}/storage/v1/object/public/{BUCKET}/crops/seg_001.jpg"
        )

        assert provider.retrieve(public) == b"downloaded-bytes"
        assert provider.calls[0]["path"] == (
            "/storage/v1/object/ifne/crops/seg_001.jpg"
        )

    def test_accepts_a_bare_key(self) -> None:
        provider = make_provider()

        provider.retrieve("crops/seg_001.jpg")

        assert provider.calls[0]["path"] == (
            "/storage/v1/object/ifne/crops/seg_001.jpg"
        )


class TestDelete:
    def test_deletes_by_url(self) -> None:
        provider = make_provider()
        public = (
            f"{BASE_URL}/storage/v1/object/public/{BUCKET}/meal_1.jpg"
        )

        provider.delete(public)

        assert provider.calls[0]["method"] == "DELETE"
        assert provider.calls[0]["path"] == "/storage/v1/object/ifne/meal_1.jpg"

    def test_missing_object_is_logged_not_raised(self) -> None:
        provider = make_provider(RuntimeError("404 Not Found"))

        provider.delete("crops/missing.jpg")  # should not raise


class TestPublicUrl:
    def test_builds_the_public_path(self) -> None:
        provider = make_provider()

        assert provider.public_url("crops/seg_001.jpg") == (
            f"{BASE_URL}/storage/v1/object/public/{BUCKET}/crops/seg_001.jpg"
        )

    def test_trailing_slash_on_the_base_url_is_ignored(self) -> None:
        provider = SupabaseStorageProvider(f"{BASE_URL}/", "key", BUCKET)

        assert provider.public_url("x.jpg").startswith(f"{BASE_URL}/storage")
