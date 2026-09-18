"""SegmentMeal use case — segments an uploaded image into crop regions."""

import logging
from pathlib import Path

from app.domain.entities.meal import Meal
from app.domain.interfaces.meal_repository import MealRepository
from app.domain.interfaces.storage_provider import StorageProvider
from app.domain.interfaces.vision_provider import VisionProvider
from app.shared.ids import generate_id

logger = logging.getLogger(__name__)


class SegmentMealUseCase:
    """Segments an uploaded meal image into crops.

    Pipeline:
        StorageProvider → VisionProvider → Segments → Meal draft

    The resulting draft meal awaits user labels. Label suggestions are
    optional and controlled per request via the suggest_labels flag.
    """

    def __init__(
        self,
        vision_provider: VisionProvider,
        meal_repository: MealRepository,
        storage_provider: StorageProvider,
    ) -> None:
        self._vision_provider = vision_provider
        self._meal_repository = meal_repository
        self._storage_provider = storage_provider

    def execute(
        self,
        image_path: str,
        suggest_labels: bool = False,
        original_filename: str | None = None,
    ) -> Meal:
        """Segment an uploaded image and produce a draft meal.

        Args:
            image_path: Path to the uploaded image file.
            suggest_labels: When True, request label suggestions.
            original_filename: The client's original filename, preserved
                in storage when provided.

        Returns:
            The created draft Meal with unlabeled segments.
        """
        meal_id = generate_id("meal")
        base_name = Path(original_filename or image_path).name
        stored_path = self._storage_provider.store(
            source_path=image_path,
            destination_name=f"{meal_id}_{base_name}",
        )

        # The vision provider reads the image bytes, so it gets the local
        # upload: storage may be remote and hand back a URL rather than a
        # readable path.
        segments = self._vision_provider.segment(
            image_path,
            suggest_labels=suggest_labels,
            namespace=f"{meal_id}_",
        )
        logger.info(
            "Segmentation completed: %d segments (provider=%s)",
            len(segments),
            self._vision_provider.provider_name,
        )

        meal = Meal(meal_id=meal_id, image_path=stored_path)
        meal.add_segments(segments)
        meal.mark_draft()
        self._meal_repository.save(meal)
        logger.info("Meal draft created: %s", meal.meal_id)
        return meal
