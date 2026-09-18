"""VisionProvider interface — contract for all computer vision implementations."""

from abc import ABC, abstractmethod

from app.domain.entities.segment import Segment


class VisionProvider(ABC):
    """Interface that every computer vision implementation must satisfy.

    Vision providers produce Segments (crops + mask statistics). Label
    suggestions are optional and never authoritative — the user always
    decides the final label.

    Upper layers must never know which provider is currently used.
    """

    @abstractmethod
    def segment(
        self,
        image_path: str,
        suggest_labels: bool = False,
        namespace: str = "",
    ) -> list[Segment]:
        """Segment a food image into crop regions.

        Args:
            image_path: Path to the uploaded image file.
            suggest_labels: When True, attach label suggestions to each
                segment. When False, segments carry no suggestions.
            namespace: Prefix for saved crop files, so crops from
                different meals cannot overwrite each other.

        Returns:
            A list of Segment objects, one per detected food region.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this vision provider."""
        ...

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Version string of this vision provider."""
        ...
