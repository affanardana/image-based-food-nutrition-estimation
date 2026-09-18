"""SupabaseStorageProvider — object storage on Supabase Storage.

Uploaded images and crops live in a Supabase Storage bucket rather than
on the backend's disk, so the API can run on hosts without a persistent
filesystem.

The bucket is read-public: `store` returns the object's public URL, and
that URL is what the domain keeps as the image/crop reference. `delete`
and `retrieve` accept either that URL or a bare object key, so
references written before a provider switch still resolve.
"""

import logging
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

from app.domain.interfaces.storage_provider import StorageProvider

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 120

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


class SupabaseStorageProvider(StorageProvider):
    """Stores files in a Supabase Storage bucket.

    The service key is a server-side secret and bypasses row-level
    security; it must come from the environment, never from source.
    """

    def __init__(self, base_url: str, service_key: str, bucket: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_key = service_key
        self._bucket = bucket

    def store(self, source_path: str, destination_name: str) -> str:
        """Upload a file and return its public URL."""
        self._request(
            "POST",
            self._object_api_path(destination_name),
            data=Path(source_path).read_bytes(),
            content_type=_content_type(source_path),
            extra_headers={"x-upsert": "true"},
        )
        return self.public_url(destination_name)

    def retrieve(self, path: str) -> bytes:
        """Download an object by URL or key."""
        return self._request(
            "GET",
            self._object_api_path(self._object_key(path)),
        )

    def delete(self, path: str) -> None:
        """Remove an object, logging (not raising) when it is missing."""
        try:
            self._request(
                "DELETE",
                self._object_api_path(self._object_key(path)),
            )
        except RuntimeError as exc:
            logger.warning("Failed to delete stored object '%s': %s", path, exc)

    def public_url(self, object_key: str) -> str:
        """The public URL of an object in the bucket."""
        return (
            f"{self._base_url}/storage/v1/object/public/"
            f"{self._bucket}/{object_key}"
        )

    # ── Internal helpers ───────────────────────────────────────────────

    def _object_key(self, reference: str) -> str:
        """The bucket object key for a reference.

        Accepts the public URL this provider returns, an authenticated
        API URL, or a bare key.
        """
        for marker in (
            f"/object/public/{self._bucket}/",
            f"/object/{self._bucket}/",
        ):
            if marker in reference:
                return reference.split(marker, 1)[1]
        return reference.lstrip("/")

    def _object_api_path(self, object_key: str) -> str:
        return f"/storage/v1/object/{self._bucket}/{object_key}"

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> bytes:
        headers = {
            "Authorization": f"Bearer {self._service_key}",
            "apikey": self._service_key,
        }
        if content_type is not None:
            headers["Content-Type"] = content_type
        if extra_headers is not None:
            headers.update(extra_headers)

        http_request = urlrequest.Request(
            f"{self._base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urlrequest.urlopen(
                http_request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                # urlopen is typed as returning Any; the body is bytes.
                payload: bytes = response.read()
                return payload
        except (urlerror.URLError, OSError) as exc:
            raise RuntimeError(
                f"Supabase Storage request failed: {exc}"
            ) from exc


def _content_type(source_path: str) -> str:
    return _CONTENT_TYPES.get(
        Path(source_path).suffix.lower(),
        "application/octet-stream",
    )
