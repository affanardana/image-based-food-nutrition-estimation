"""Tests for SegmentMealUseCase — image segmentation into a meal draft."""

from app.application.use_cases.segment_meal import SegmentMealUseCase
from app.domain.entities.meal import MealState
from app.domain.entities.segment import Segment
from tests.application.fakes import (
    FakeMealRepository,
    FakeStorageProvider,
    FakeVisionProvider,
)
from tests.helpers import make_segment


def build_use_case(
    segments: list[Segment],
) -> tuple[
    SegmentMealUseCase,
    FakeMealRepository,
    FakeStorageProvider,
    FakeVisionProvider,
]:
    """Assemble a SegmentMealUseCase with fakes."""
    repo = FakeMealRepository()
    storage = FakeStorageProvider()
    provider = FakeVisionProvider(segments)
    use_case = SegmentMealUseCase(
        vision_provider=provider,
        meal_repository=repo,
        storage_provider=storage,
    )
    return use_case, repo, storage, provider


class TestSegmentMealUseCase:
    def test_produces_draft_meal_with_segments(self) -> None:
        use_case, repo, storage, _ = build_use_case(
            [make_segment("seg_001"), make_segment("seg_002")]
        )

        meal = use_case.execute("/tmp/upload.jpg")

        assert meal.state == MealState.DRAFT
        assert len(meal.segments) == 2
        assert meal.food_items == []
        assert meal.nutrition_summary.total_calories_kcal == 0.0

        # Image stored and meal persisted
        assert len(storage.stored) == 1
        assert repo.get_by_id(meal.meal_id) is meal

    def test_suggest_labels_flag_forwarded(self) -> None:
        use_case, _, _, provider = build_use_case(
            [make_segment("seg_001", suggestion_label="sate")]
        )

        meal = use_case.execute("/tmp/upload.jpg", suggest_labels=True)

        assert len(provider.segment_calls) == 1
        vision_path, flag = provider.segment_calls[0]
        assert flag is True
        # The vision provider reads the image bytes, so it receives the
        # local upload: storage may be remote and return a URL.
        assert vision_path == "/tmp/upload.jpg"
        # The meal keeps the storage reference.
        assert meal.image_path.startswith("/storage/meal_")
        assert meal.image_path.endswith("_upload.jpg")

    def test_suggest_labels_defaults_to_false(self) -> None:
        use_case, _, _, provider = build_use_case([make_segment("seg_001")])

        use_case.execute("/tmp/upload.jpg")

        assert len(provider.segment_calls) == 1
        _, flag = provider.segment_calls[0]
        assert flag is False

    def test_segments_retain_crop_references(self) -> None:
        use_case, _, _, _ = build_use_case(
            [
                make_segment("seg_001"),
                make_segment("seg_002"),
            ]
        )

        meal = use_case.execute("/tmp/upload.jpg")

        # Crops are namespaced by meal so analyses cannot overwrite
        # each other's crop files.
        assert {s.crop_image_ref for s in meal.segments} == {
            f"/crops/{meal.meal_id}_seg_001.jpg",
            f"/crops/{meal.meal_id}_seg_002.jpg",
        }
