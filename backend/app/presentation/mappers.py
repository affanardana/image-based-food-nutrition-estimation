"""Mappers from domain entities to presentation schemas."""

from pathlib import Path

from app.domain.entities.food_item import FoodItem
from app.domain.entities.meal import Meal
from app.domain.entities.segment import Segment
from app.presentation.schemas.meal import (
    BoundingBoxOut,
    CanonicalFoodOut,
    FoodItemOut,
    HistoryEntryOut,
    MealData,
    MeasurementOut,
    NutritionOut,
    SegmentOut,
    SuggestionOut,
    SummaryOut,
)

IMAGE_URL_PREFIX = "/api/v1/images"


def stored_path_to_url(storage_base: str | None, stored_path: str) -> str:
    """Convert a storage path into its public image URL.

    Vision providers store crop references as filesystem paths; the
    frontend needs URL-shaped references served by the static mount.
    References that are already URL-shaped (e.g. the mock provider's
    ``/api/v1/images/...``) and paths outside the storage base pass
    through unchanged.
    """
    if not stored_path or stored_path.startswith("/") or storage_base is None:
        return stored_path
    try:
        relative = Path(stored_path).resolve().relative_to(
            Path(storage_base).resolve()
        )
    except ValueError:
        return stored_path
    return f"{IMAGE_URL_PREFIX}/{relative.as_posix()}"


def meal_to_data(meal: Meal, storage_base: str | None = None) -> MealData:
    """Serialize a meal aggregate into the API response shape."""
    return MealData(
        meal_id=meal.meal_id,
        state=meal.state.value,
        name=meal.name,
        image_url=(
            f"{IMAGE_URL_PREFIX}/{Path(meal.image_path).name}"
            if meal.image_path
            else None
        ),
        segments=[
            segment_to_out(s, storage_base) for s in meal.segments
        ],
        food_items=[food_item_to_out(i) for i in meal.food_items],
        summary=summary_to_out(meal),
        created_at=meal.created_at,
        updated_at=meal.updated_at,
    )


def history_entry_to_out(
    meal: Meal,
    storage_base: str | None = None,
) -> HistoryEntryOut:
    """Serialize one meal into a compact history row."""
    return HistoryEntryOut(
        meal_id=meal.meal_id,
        state=meal.state.value,
        name=meal.name,
        created_at=meal.created_at,
        updated_at=meal.updated_at,
        image_url=(
            f"{IMAGE_URL_PREFIX}/{Path(meal.image_path).name}"
            if meal.image_path
            else None
        ),
        total_calories_kcal=meal.nutrition_summary.total_calories_kcal,
        food_item_count=len(meal.food_items),
        segment_count=len(meal.segments),
    )


def segment_to_out(
    segment: Segment,
    storage_base: str | None = None,
) -> SegmentOut:
    """Serialize a vision segment."""
    suggestion = None
    if segment.suggestion is not None:
        suggestion = SuggestionOut(
            label=segment.suggestion.vision_class.label,
            confidence=segment.suggestion.confidence.value,
        )
    return SegmentOut(
        id=segment.segment_id,
        crop_url=stored_path_to_url(storage_base, segment.crop_image_ref),
        bbox=BoundingBoxOut(
            x=segment.bounding_box.x,
            y=segment.bounding_box.y,
            width=segment.bounding_box.width,
            height=segment.bounding_box.height,
        ),
        suggestion=suggestion,
    )


def food_item_to_out(item: FoodItem) -> FoodItemOut:
    """Serialize a labeled food item."""
    canonical_food = None
    if item.canonical_food is not None:
        canonical_food = CanonicalFoodOut(
            id=item.canonical_food.id,
            name=item.canonical_food.name,
        )
    measurement = MeasurementOut(
        estimated_volume_cm3=(
            item.measurement.volume.value_cm3
            if item.measurement.volume is not None
            else None
        ),
        estimated_weight_g=(
            item.measurement.weight.value_g
            if item.measurement.weight is not None
            else None
        ),
    )
    nutrition = NutritionOut(
        calories_kcal=item.nutrition_profile.calories_kcal,
        protein_g=item.nutrition_profile.protein_g,
        fat_g=item.nutrition_profile.fat_g,
        carbohydrates_g=item.nutrition_profile.carbohydrates_g,
        fiber_g=item.nutrition_profile.fiber_g,
        sodium_mg=item.nutrition_profile.sodium_mg,
    )
    return FoodItemOut(
        id=item.food_item_id,
        canonical_food=canonical_food,
        segment_ids=[s.segment_id for s in item.segments],
        measurement=measurement,
        nutrition=nutrition,
        ingredients=[i.name for i in item.ingredients],
    )


def summary_to_out(meal: Meal) -> SummaryOut:
    """Serialize the meal's nutrition summary."""
    summary = meal.nutrition_summary
    return SummaryOut(
        total_calories_kcal=summary.total_calories_kcal,
        total_protein_g=summary.total_protein_g,
        total_fat_g=summary.total_fat_g,
        total_carbohydrates_g=summary.total_carbohydrates_g,
        total_fiber_g=summary.total_fiber_g,
        total_sodium_mg=summary.total_sodium_mg,
    )
