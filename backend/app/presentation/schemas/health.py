"""Health check schemas."""

from pydantic import BaseModel


class HealthData(BaseModel):
    service: str
