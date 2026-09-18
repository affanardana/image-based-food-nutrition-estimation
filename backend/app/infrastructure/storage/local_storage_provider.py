"""LocalStorageProvider — stores images on the local filesystem."""

import shutil
from pathlib import Path

from app.domain.interfaces.storage_provider import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Stores uploaded images and crops on the local filesystem."""

    def __init__(self, base_path: str) -> None:
        self._base_path = Path(base_path)

    def store(self, source_path: str, destination_name: str) -> str:
        """Copy the source file into the storage directory.

        Creates intermediate directories so nested destinations
        (e.g. ``crops/seg_001.jpg``) work without extra setup.

        Returns the stored path, which is used as the image reference.
        """
        target = self._base_path / destination_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, target)
        return str(target)

    def retrieve(self, path: str) -> bytes:
        """Return the raw bytes stored at the given path."""
        return Path(path).read_bytes()

    def delete(self, path: str) -> None:
        """Remove the stored file, ignoring a missing file."""
        Path(path).unlink(missing_ok=True)
