"""Common response envelope schemas."""

from typing import Literal

from pydantic import BaseModel


class SuccessEnvelope[T](BaseModel):
    """Successful response wrapper: {"status": "success", "data": ...}."""

    status: Literal["success"] = "success"
    data: T


class ErrorBody(BaseModel):
    """Error detail: {"code": ..., "message": ...}."""

    code: str
    message: str


class ErrorEnvelope(BaseModel):
    """Error response wrapper: {"status": "error", "error": ...}."""

    status: Literal["error"] = "error"
    error: ErrorBody
