"""Meal endpoints: analyze, label, retrieve, correct, delete."""

import tempfile
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from app.application.use_cases.label_segments import SegmentLabelAssignmentRequest
from app.application.use_cases.update_meal import FoodItemCorrectionRequest
from app.presentation.dependencies import get_dependencies
from app.presentation.errors import APIError
from app.presentation.image_info import read_image_dimensions
from app.presentation.mappers import history_entry_to_out, meal_to_data
from app.presentation.schemas.common import SuccessEnvelope
from app.presentation.schemas.meal import (
    AnalyzeMealData,
    CorrectionRequest,
    DeletedData,
    DiscardSegmentsRequest,
    HistoryEntryOut,
    ImageInfoOut,
    LabelMealRequest,
    MealData,
)

router = APIRouter(tags=["meals"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}


async def _read_upload(
    request: Request,
    image: UploadFile,
) -> bytes:
    """Validate and read the uploaded image bytes."""
    if image.content_type not in _ALLOWED_CONTENT_TYPES:
        raise APIError(
            415,
            "UNSUPPORTED_IMAGE",
            f"Unsupported image format: {image.content_type}. "
            "Only JPEG and PNG are supported.",
        )
    content = await image.read()
    deps = get_dependencies(request)
    max_bytes = deps.config.storage.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise APIError(
            413,
            "IMAGE_TOO_LARGE",
            f"Uploaded image exceeds the limit of "
            f"{deps.config.storage.max_upload_size_mb} MB.",
        )
    return content


@router.post(
    "/meals/analyze",
    response_model=SuccessEnvelope[AnalyzeMealData],
)
async def analyze_meal(
    request: Request,
    image: Annotated[UploadFile, File()],
    suggest_labels: Annotated[bool, Form()] = False,
) -> SuccessEnvelope[AnalyzeMealData]:
    """Segment an uploaded meal image into a draft meal."""
    content = await _read_upload(request, image)

    suffix = Path(image.filename or "upload").suffix or ".img"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        deps = get_dependencies(request)
        start = time.perf_counter()
        meal = deps.segment_meal.execute(
            tmp_path,
            suggest_labels=suggest_labels,
            original_filename=image.filename,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    dimensions = read_image_dimensions(content)
    data = meal_to_data(meal, storage_base=deps.config.storage.base_path)
    return SuccessEnvelope(
        data=AnalyzeMealData(
            **data.model_dump(),
            processing_time_ms=elapsed_ms,
            image=ImageInfoOut(
                width=dimensions[0] if dimensions else None,
                height=dimensions[1] if dimensions else None,
            ),
        )
    )


@router.get(
    "/meals",
    response_model=SuccessEnvelope[list[HistoryEntryOut]],
)
def list_meals(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SuccessEnvelope[list[HistoryEntryOut]]:
    """List stored meals, newest first."""
    deps = get_dependencies(request)
    meals = deps.list_meals.execute(limit=limit, offset=offset)
    storage_base = deps.config.storage.base_path
    return SuccessEnvelope(
        data=[history_entry_to_out(meal, storage_base) for meal in meals]
    )


def _to_assignments(
    body: LabelMealRequest,
) -> list[SegmentLabelAssignmentRequest]:
    """Translate a label request body into use case input."""
    return [
        {
            "canonical_food_id": assignment.canonical_food_id,
            "segment_ids": assignment.segment_ids,
        }
        for assignment in body.assignments
    ]


@router.post(
    "/meals/{meal_id}/label",
    response_model=SuccessEnvelope[MealData],
)
def label_meal(
    request: Request,
    meal_id: str,
    body: LabelMealRequest,
) -> SuccessEnvelope[MealData]:
    """Assign canonical food labels to segments."""
    deps = get_dependencies(request)
    meal = deps.label_segments.execute(
        meal_id,
        _to_assignments(body),
        name=body.name,
    )
    return SuccessEnvelope(
        data=meal_to_data(meal, storage_base=deps.config.storage.base_path)
    )


@router.put(
    "/meals/{meal_id}/labels",
    response_model=SuccessEnvelope[MealData],
)
def replace_meal_labels(
    request: Request,
    meal_id: str,
    body: LabelMealRequest,
) -> SuccessEnvelope[MealData]:
    """Replace the labeling of a stored meal (edit flow)."""
    deps = get_dependencies(request)
    meal = deps.label_segments.execute(
        meal_id,
        _to_assignments(body),
        replace=True,
        name=body.name,
    )
    return SuccessEnvelope(
        data=meal_to_data(meal, storage_base=deps.config.storage.base_path)
    )


@router.get(
    "/meals/{meal_id}",
    response_model=SuccessEnvelope[MealData],
)
def get_meal(
    request: Request,
    meal_id: str,
) -> SuccessEnvelope[MealData]:
    """Retrieve a previously analyzed meal."""
    deps = get_dependencies(request)
    meal = deps.get_meal.execute(meal_id)
    return SuccessEnvelope(
        data=meal_to_data(meal, storage_base=deps.config.storage.base_path)
    )


@router.patch(
    "/meals/{meal_id}",
    response_model=SuccessEnvelope[MealData],
)
def correct_meal(
    request: Request,
    meal_id: str,
    body: CorrectionRequest,
) -> SuccessEnvelope[MealData]:
    """Apply user corrections to food items and recalculate nutrition."""
    deps = get_dependencies(request)
    corrections: list[FoodItemCorrectionRequest] = []
    for item in body.food_items:
        correction: FoodItemCorrectionRequest = {"food_item_id": item.id}
        if item.canonical_food is not None:
            correction["canonical_food_id"] = item.canonical_food
        if item.estimated_weight_g is not None:
            correction["estimated_weight_g"] = item.estimated_weight_g
        if item.ingredients is not None:
            correction["ingredients"] = item.ingredients
        corrections.append(correction)
    meal = deps.update_meal.execute(meal_id, corrections, name=body.name)
    return SuccessEnvelope(
        data=meal_to_data(meal, storage_base=deps.config.storage.base_path)
    )


@router.post(
    "/meals/{meal_id}/segments/discard",
    response_model=SuccessEnvelope[MealData],
)
def discard_segments(
    request: Request,
    meal_id: str,
    body: DiscardSegmentsRequest,
) -> SuccessEnvelope[MealData]:
    """Discard one or more segments (bad segmentation or unknown food)."""
    deps = get_dependencies(request)
    meal = deps.discard_segments.execute(meal_id, body.segment_ids)
    return SuccessEnvelope(
        data=meal_to_data(meal, storage_base=deps.config.storage.base_path)
    )


@router.delete(
    "/meals/{meal_id}",
    response_model=SuccessEnvelope[DeletedData],
)
def delete_meal(
    request: Request,
    meal_id: str,
) -> SuccessEnvelope[DeletedData]:
    """Delete an existing meal."""
    deps = get_dependencies(request)
    deps.delete_meal.execute(meal_id)
    return SuccessEnvelope(data=DeletedData(deleted=True))
