"""SqlMealRepository — the Meal aggregate stored in a SQL database.

Production uses Supabase (Postgres); tests use SQLite. The whole
aggregate is written on every save (children are replaced, not patched),
which keeps the stored meal exactly equal to the domain object and
avoids partial-update bugs at this scale.

Child rows are deleted explicitly in dependency order rather than by
relying on ON DELETE CASCADE: SQLite (used in tests) does not enforce
foreign keys by default, so cascades would behave differently in tests
than in production.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, delete, insert, select
from sqlalchemy.engine import Connection, RowMapping

from app.domain.entities.canonical_food import CanonicalFood
from app.domain.entities.food_item import CorrectionState, FoodItem
from app.domain.entities.ingredient import Ingredient, IngredientSource
from app.domain.entities.meal import Meal, MealState
from app.domain.entities.measurement import Measurement
from app.domain.entities.nutrition_summary import NutritionSummary
from app.domain.entities.physical_property import PhysicalProperty
from app.domain.entities.segment import Segment, SegmentSuggestion
from app.domain.entities.user_correction import UserCorrection
from app.domain.entities.vision_class import VisionClass
from app.domain.interfaces.meal_repository import MealRepository
from app.domain.values.bounding_box import BoundingBox
from app.domain.values.confidence_score import ConfidenceScore
from app.domain.values.measurement_values import Area, Volume, Weight
from app.domain.values.nutrition_values import NutritionProfile
from app.infrastructure.persistence.schema import (
    food_item_corrections,
    food_item_ingredients,
    food_item_segments,
    food_items,
    meals,
    segments,
)


class SqlMealRepository(MealRepository):
    """Meal persistence backed by a SQL database."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, meal: Meal) -> None:
        """Write the full aggregate, replacing any stored version."""
        with self._engine.begin() as connection:
            _delete_meal(connection, meal.meal_id)
            connection.execute(insert(meals), [_meal_row(meal)])
            if meal.segments:
                connection.execute(
                    insert(segments),
                    [_segment_row(meal.meal_id, s) for s in meal.segments],
                )
            if meal.food_items:
                connection.execute(
                    insert(food_items),
                    [
                        _food_item_row(meal.meal_id, position, item)
                        for position, item in enumerate(meal.food_items)
                    ],
                )
                _insert_children(connection, meal)

    def get_by_id(self, meal_id: str) -> Meal | None:
        with self._engine.connect() as connection:
            rows = connection.execute(
                select(meals).where(meals.c.meal_id == meal_id)
            ).mappings().all()
            if not rows:
                return None
            return _load_meals(connection, rows)[0]

    def list_recent(self, limit: int = 20, offset: int = 0) -> list[Meal]:
        """Return stored meals, newest first, in a fixed number of queries."""
        statement = (
            select(meals)
            .order_by(meals.c.created_at.desc(), meals.c.meal_id.desc())
            .limit(limit)
            .offset(offset)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
            if not rows:
                return []
            return _load_meals(connection, rows)

    def delete(self, meal_id: str) -> None:
        with self._engine.begin() as connection:
            _delete_meal(connection, meal_id)

    def exists(self, meal_id: str) -> bool:
        statement = select(meals.c.meal_id).where(meals.c.meal_id == meal_id)
        with self._engine.connect() as connection:
            return connection.execute(statement).first() is not None


# ── Writing ────────────────────────────────────────────────────────────


def _delete_meal(connection: Connection, meal_id: str) -> None:
    """Remove a meal and every child row, children first."""
    item_ids = select(food_items.c.food_item_id).where(
        food_items.c.meal_id == meal_id
    )
    connection.execute(
        delete(food_item_corrections).where(
            food_item_corrections.c.food_item_id.in_(item_ids)
        )
    )
    connection.execute(
        delete(food_item_ingredients).where(
            food_item_ingredients.c.food_item_id.in_(item_ids)
        )
    )
    connection.execute(
        delete(food_item_segments).where(food_item_segments.c.meal_id == meal_id)
    )
    connection.execute(delete(food_items).where(food_items.c.meal_id == meal_id))
    connection.execute(delete(segments).where(segments.c.meal_id == meal_id))
    connection.execute(delete(meals).where(meals.c.meal_id == meal_id))


def _insert_children(connection: Connection, meal: Meal) -> None:
    """Insert segment groupings, ingredients, and corrections."""
    links = [
        {
            "food_item_id": item.food_item_id,
            "meal_id": meal.meal_id,
            "segment_id": segment.segment_id,
        }
        for item in meal.food_items
        for segment in item.segments
    ]
    if links:
        connection.execute(insert(food_item_segments), links)

    ingredients = [
        {
            "food_item_id": item.food_item_id,
            "position": position,
            "name": ingredient.name,
            "source": ingredient.source.value,
        }
        for item in meal.food_items
        for position, ingredient in enumerate(item.ingredients)
    ]
    if ingredients:
        connection.execute(insert(food_item_ingredients), ingredients)

    corrections = [
        {
            "food_item_id": item.food_item_id,
            "field": correction.field,
            "old_value": correction.old_value,
            "new_value": correction.new_value,
            "created_at": correction.timestamp,
        }
        for item in meal.food_items
        for correction in item.corrections
    ]
    if corrections:
        connection.execute(insert(food_item_corrections), corrections)


def _meal_row(meal: Meal) -> dict[str, Any]:
    summary = meal.nutrition_summary
    return {
        "meal_id": meal.meal_id,
        "image_path": meal.image_path,
        "name": meal.name,
        "state": meal.state.value,
        "created_at": meal.created_at,
        "updated_at": meal.updated_at,
        "total_calories_kcal": summary.total_calories_kcal,
        "total_protein_g": summary.total_protein_g,
        "total_fat_g": summary.total_fat_g,
        "total_carbohydrates_g": summary.total_carbohydrates_g,
        "total_fiber_g": summary.total_fiber_g,
        "total_sodium_mg": summary.total_sodium_mg,
    }


def _segment_row(meal_id: str, segment: Segment) -> dict[str, Any]:
    suggestion = segment.suggestion
    return {
        "meal_id": meal_id,
        "segment_id": segment.segment_id,
        "crop_image_ref": segment.crop_image_ref,
        "mask_area_px": segment.mask_area_px,
        "normalized_area": segment.normalized_area,
        "bbox_x": segment.bounding_box.x,
        "bbox_y": segment.bounding_box.y,
        "bbox_width": segment.bounding_box.width,
        "bbox_height": segment.bounding_box.height,
        "max_normalized_depth": segment.max_normalized_depth,
        "provider_name": segment.provider_name,
        "provider_version": segment.provider_version,
        "suggestion_label": (
            suggestion.vision_class.label if suggestion is not None else None
        ),
        "suggestion_confidence": (
            suggestion.confidence.value if suggestion is not None else None
        ),
    }


def _food_item_row(
    meal_id: str,
    position: int,
    item: FoodItem,
) -> dict[str, Any]:
    food = item.canonical_food
    properties = food.physical_properties if food is not None else None
    profile = item.nutrition_profile
    return {
        "food_item_id": item.food_item_id,
        "meal_id": meal_id,
        "position": position,
        "canonical_food_id": food.id if food is not None else None,
        "canonical_food_name": food.name if food is not None else None,
        "canonical_food_typical_weight_g": (
            food.typical_weight_g if food is not None else None
        ),
        "canonical_food_density_g_per_cm3": (
            properties.density_g_per_cm3 if properties is not None else None
        ),
        "canonical_food_calibration_factor": (
            properties.calibration_factor if properties is not None else None
        ),
        "correction_state": item.correction_state.value,
        "area_cm2": item.measurement.area.value_cm2
        if item.measurement.area is not None
        else None,
        "volume_cm3": item.measurement.volume.value_cm3
        if item.measurement.volume is not None
        else None,
        "weight_g": item.measurement.weight.value_g
        if item.measurement.weight is not None
        else None,
        "calories_kcal": profile.calories_kcal,
        "protein_g": profile.protein_g,
        "fat_g": profile.fat_g,
        "carbohydrates_g": profile.carbohydrates_g,
        "fiber_g": profile.fiber_g,
        "sodium_mg": profile.sodium_mg,
    }


# ── Reading ────────────────────────────────────────────────────────────


def _load_meals(
    connection: Connection,
    meal_rows: Sequence[RowMapping],
) -> list[Meal]:
    """Assemble meals and their children using one query per table."""
    meal_ids = [row["meal_id"] for row in meal_rows]

    segment_rows = (
        connection.execute(
            select(segments)
            .where(segments.c.meal_id.in_(meal_ids))
            .order_by(segments.c.meal_id, segments.c.segment_id)
        )
        .mappings()
        .all()
    )
    item_rows = (
        connection.execute(
            select(food_items)
            .where(food_items.c.meal_id.in_(meal_ids))
            .order_by(food_items.c.meal_id, food_items.c.position)
        )
        .mappings()
        .all()
    )
    item_ids = [row["food_item_id"] for row in item_rows]

    link_rows = (
        connection.execute(
            select(food_item_segments)
            .where(food_item_segments.c.meal_id.in_(meal_ids))
            .order_by(
                food_item_segments.c.food_item_id,
                food_item_segments.c.segment_id,
            )
        )
        .mappings()
        .all()
    )
    ingredient_rows = (
        connection.execute(
            select(food_item_ingredients)
            .where(food_item_ingredients.c.food_item_id.in_(item_ids))
            .order_by(
                food_item_ingredients.c.food_item_id,
                food_item_ingredients.c.position,
            )
        )
        .mappings()
        .all()
        if item_ids
        else []
    )
    correction_rows = (
        connection.execute(
            select(food_item_corrections)
            .where(food_item_corrections.c.food_item_id.in_(item_ids))
            .order_by(food_item_corrections.c.correction_id)
        )
        .mappings()
        .all()
        if item_ids
        else []
    )

    segments_by_meal: dict[str, dict[str, Segment]] = {}
    for row in segment_rows:
        segment = _to_segment(row)
        segments_by_meal.setdefault(row["meal_id"], {})[
            segment.segment_id
        ] = segment

    segments_by_item: dict[str, list[str]] = {}
    for row in link_rows:
        segments_by_item.setdefault(row["food_item_id"], []).append(
            row["segment_id"]
        )

    ingredients_by_item: dict[str, list[Ingredient]] = {}
    for row in ingredient_rows:
        ingredients_by_item.setdefault(row["food_item_id"], []).append(
            Ingredient(
                name=row["name"],
                source=IngredientSource(row["source"]),
            )
        )

    corrections_by_item: dict[str, list[UserCorrection]] = {}
    for row in correction_rows:
        corrections_by_item.setdefault(row["food_item_id"], []).append(
            UserCorrection(
                field=row["field"],
                old_value=row["old_value"],
                new_value=row["new_value"],
                timestamp=_as_utc(row["created_at"]),
            )
        )

    items_by_meal: dict[str, list[FoodItem]] = {}
    for row in item_rows:
        meal_id = row["meal_id"]
        meal_segments = segments_by_meal.get(meal_id, {})
        item_id = row["food_item_id"]
        items_by_meal.setdefault(meal_id, []).append(
            _to_food_item(
                row,
                segments=[
                    meal_segments[segment_id]
                    for segment_id in segments_by_item.get(item_id, [])
                    if segment_id in meal_segments
                ],
                ingredients=ingredients_by_item.get(item_id, []),
                corrections=corrections_by_item.get(item_id, []),
            )
        )

    return [
        _to_meal(
            row,
            segments=list(segments_by_meal.get(row["meal_id"], {}).values()),
            food_items=items_by_meal.get(row["meal_id"], []),
        )
        for row in meal_rows
    ]


def _to_meal(
    row: RowMapping,
    segments: list[Segment],
    food_items: list[FoodItem],
) -> Meal:
    return Meal(
        meal_id=row["meal_id"],
        image_path=row["image_path"],
        name=row["name"] or "",
        segments=segments,
        food_items=food_items,
        nutrition_summary=NutritionSummary(
            total_calories_kcal=row["total_calories_kcal"],
            total_protein_g=row["total_protein_g"],
            total_fat_g=row["total_fat_g"],
            total_carbohydrates_g=row["total_carbohydrates_g"],
            total_fiber_g=row["total_fiber_g"],
            total_sodium_mg=row["total_sodium_mg"],
        ),
        state=MealState(row["state"]),
        created_at=_as_utc(row["created_at"]),
        updated_at=_as_utc(row["updated_at"]),
    )


def _to_segment(row: RowMapping) -> Segment:
    suggestion = None
    if (
        row["suggestion_label"] is not None
        and row["suggestion_confidence"] is not None
    ):
        suggestion = SegmentSuggestion(
            vision_class=VisionClass(label=row["suggestion_label"]),
            confidence=ConfidenceScore(value=row["suggestion_confidence"]),
        )
    return Segment(
        segment_id=row["segment_id"],
        crop_image_ref=row["crop_image_ref"],
        mask_area_px=row["mask_area_px"],
        normalized_area=row["normalized_area"],
        bounding_box=BoundingBox(
            x=row["bbox_x"],
            y=row["bbox_y"],
            width=row["bbox_width"],
            height=row["bbox_height"],
        ),
        max_normalized_depth=row["max_normalized_depth"],
        provider_name=row["provider_name"],
        provider_version=row["provider_version"],
        suggestion=suggestion,
    )


def _to_food_item(
    row: RowMapping,
    segments: list[Segment],
    ingredients: list[Ingredient],
    corrections: list[UserCorrection],
) -> FoodItem:
    canonical_food = None
    if row["canonical_food_id"] is not None and row["canonical_food_name"]:
        typical_weight = row["canonical_food_typical_weight_g"]
        canonical_food = CanonicalFood(
            id=row["canonical_food_id"],
            name=row["canonical_food_name"],
            typical_weight_g=(
                typical_weight if typical_weight is not None else 150.0
            ),
            physical_properties=PhysicalProperty(
                density_g_per_cm3=row["canonical_food_density_g_per_cm3"],
                calibration_factor=row["canonical_food_calibration_factor"],
            ),
        )

    measurement = Measurement()
    if row["area_cm2"] is not None:
        measurement.update_area(Area(value_cm2=row["area_cm2"]))
    if row["volume_cm3"] is not None:
        measurement.update_volume(Volume(value_cm3=row["volume_cm3"]))
    if row["weight_g"] is not None:
        measurement.update_weight(Weight(value_g=row["weight_g"]))

    return FoodItem(
        food_item_id=row["food_item_id"],
        canonical_food=canonical_food,
        segments=segments,
        measurement=measurement,
        ingredients=ingredients,
        nutrition_profile=NutritionProfile(
            calories_kcal=row["calories_kcal"],
            protein_g=row["protein_g"],
            fat_g=row["fat_g"],
            carbohydrates_g=row["carbohydrates_g"],
            fiber_g=row["fiber_g"],
            sodium_mg=row["sodium_mg"],
        ),
        correction_state=CorrectionState(row["correction_state"]),
        corrections=corrections,
    )


def _as_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime.

    SQLite discards tzinfo on storage, so rows read back from the test
    database would otherwise be naive while domain timestamps are aware.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
