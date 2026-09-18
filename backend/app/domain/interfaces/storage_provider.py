"""StorageProvider interface — contract for image storage."""

from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """Interface for storing and retrieving uploaded images.

    Implementations may use local filesystem, S3, or any cloud storage.
    """

    @abstractmethod
    def store(self, source_path: str, destination_name: str) -> str:
        """Store an image and return its accessible path or URL.

        Args:
            source_path: Path to the temporary uploaded file.
            destination_name: Desired filename for storage.

        Returns:
            The path or URL where the image can be retrieved.
        """
        ...

    @abstractmethod
    def retrieve(self, path: str) -> bytes:
        """Retrieve image data by its stored path.

        Args:
            path: The path returned by store().

        Returns:
            Raw image bytes.
        """
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        """Remove a stored image.

        Args:
            path: The path returned by store().
        """
        ...
