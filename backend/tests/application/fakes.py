"""In-memory fakes of domain interfaces for application tests."""

from dataclasses import replace

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.meal import Meal
from app.domain.entities.segment import Segment
from app.domain.entities.vision_class import VisionClass
from app.domain.exceptions import NutritionUnavailableError
from app.domain.interfaces.canonical_food_catalog import CanonicalFoodCatalog
from app.domain.interfaces.meal_repository import MealRepository
from app.domain.interfaces.nutrition_provider import NutritionProvider
from app.domain.interfaces.storage_provider import StorageProvider
from app.domain.interfaces.vision_provider import VisionProvider
from app.domain.values.nutrition_values import NutritionProfile


class FakeVisionProvider(VisionProvider):
    """Returns a fixed list of segments and records calls."""

    def __init__(self, segments: list[Segment]) -> None:
        self._segments = segments
        self.segment_calls: list[tuple[str, bool]] = []

    def segment(
        self,
        image_path: str,
        suggest_labels: bool = False,
        namespace: str = "",
    ) -> list[Segment]:
        self.segment_calls.append((image_path, suggest_labels))
        segments = [
            replace(
                segment,
                crop_image_ref=(
                    f"/crops/{namespace}{segment.segment_id}.jpg"
                ),
            )
            for segment in self._segments
        ]
        if suggest_labels:
            return segments
        return [replace(segment, suggestion=None) for segment in segments]

    @property
    def provider_name(self) -> str:
        return "fake_vision"

    @property
    def provider_version(self) -> str:
        return "1.0.0"


class FakeNutritionProvider(NutritionProvider):
    """Returns per-100g profiles from a fixed lookup table."""

    def __init__(self, profiles: dict[str, NutritionProfile]) -> None:
        self._profiles = profiles

    def get_nutrition_per_100g(
        self,
        canonical_food: CanonicalFood,
    ) -> NutritionProfile:
        profile = self._profiles.get(canonical_food.id)
        if profile is None:
            raise NutritionUnavailableError(
                f"No nutrition data for '{canonical_food.id}'"
            )
        return profile

    @property
    def provider_name(self) -> str:
        return "fake_nutrition"


class FakeCatalog(CanonicalFoodCatalog):
    """In-memory canonical food catalog with a vision-label mapping."""

    def __init__(
        self,
        foods: list[CanonicalFood],
        vision_mapping: dict[str, str],
    ) -> None:
        self._foods = {food.id: food for food in foods}
        self._vision_mapping = vision_mapping

    def map_from_vision_class(
        self,
        vision_class: VisionClass,
    ) -> CanonicalFood | None:
        canonical_id = self._vision_mapping.get(vision_class.label)
        if canonical_id is None:
            return None
        return self._foods.get(canonical_id)

    def get_by_id(self, canonical_food_id: str) -> CanonicalFood | None:
        return self._foods.get(canonical_food_id)

    def search(self, query: str, limit: int = 20) -> list[CanonicalFood]:
        keyword = query.strip().lower()
        results = [
            food
            for food in self._foods.values()
            if keyword in food.id.lower() or keyword in food.name.lower()
        ]
        # Mirror the real catalogs: prefix matches rank first.
        results.sort(
            key=lambda food: (
                0 if food.name.lower().startswith(keyword) else 1,
                food.name,
            )
        )
        return results[:limit]

    def list_detectable_foods(self) -> list[CanonicalFood]:
        detectable_ids = set(self._vision_mapping.values())
        results = [
            food
            for food_id, food in self._foods.items()
            if food_id in detectable_ids
        ]
        results.sort(key=lambda food: food.name)
        return results


class FakeMealRepository(MealRepository):
    """In-memory meal repository."""

    def __init__(self) -> None:
        self._meals: dict[str, Meal] = {}
        self.deleted_ids: list[str] = []

    def save(self, meal: Meal) -> None:
        self._meals[meal.meal_id] = meal

    def get_by_id(self, meal_id: str) -> Meal | None:
        return self._meals.get(meal_id)

    def list_recent(self, limit: int = 20, offset: int = 0) -> list[Meal]:
        meals = sorted(
            self._meals.values(),
            key=lambda meal: meal.created_at,
            reverse=True,
        )
        return meals[offset : offset + limit]

    def delete(self, meal_id: str) -> None:
        self.deleted_ids.append(meal_id)
        self._meals.pop(meal_id, None)

    def exists(self, meal_id: str) -> bool:
        return meal_id in self._meals


class FakeStorageProvider(StorageProvider):
    """Records storage calls without touching the filesystem."""

    def __init__(self) -> None:
        self.stored: list[tuple[str, str]] = []
        self.deleted: list[str] = []

    def store(self, source_path: str, destination_name: str) -> str:
        stored_path = f"/storage/{destination_name}"
        self.stored.append((source_path, destination_name))
        return stored_path

    def retrieve(self, path: str) -> bytes:
        return b"image-bytes"

    def delete(self, path: str) -> None:
        self.deleted.append(path)
