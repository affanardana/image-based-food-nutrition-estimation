"""Canonical food search endpoint."""

from fastapi import APIRouter, Query, Request

from app.presentation.dependencies import get_dependencies
from app.presentation.schemas.common import SuccessEnvelope
from app.presentation.schemas.meal import CanonicalFoodOut

router = APIRouter(tags=["foods"])


@router.get("/foods/search", response_model=SuccessEnvelope[list[CanonicalFoodOut]])
def search_foods(
    request: Request,
    q: str = Query(default="", description="Search keyword"),
    limit: int = Query(default=20, ge=1, le=100),
) -> SuccessEnvelope[list[CanonicalFoodOut]]:
    """Search available canonical foods."""
    deps = get_dependencies(request)
    foods = deps.search_foods.execute(q, limit=limit)
    return SuccessEnvelope(
        data=[
            CanonicalFoodOut(id=food.id, name=food.name)
            for food in foods
        ]
    )
