"""Health check endpoint."""

from fastapi import APIRouter

from app.presentation.schemas.common import SuccessEnvelope
from app.presentation.schemas.health import HealthData

router = APIRouter(tags=["health"])


@router.get("/health", response_model=SuccessEnvelope[HealthData])
def health() -> SuccessEnvelope[HealthData]:
    """Return a simple service health check."""
    return SuccessEnvelope(data=HealthData(service="healthy"))
