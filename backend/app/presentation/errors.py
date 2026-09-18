"""API error types and FastAPI exception handlers.

Translates domain errors into the response envelope defined in API_SPEC.md.
Infrastructure exceptions never reach clients directly.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    FoodNotFoundError,
    MealNotFoundError,
    NutritionUnavailableError,
    UnsupportedFoodError,
)


class APIError(Exception):
    """A presentation-level error with an HTTP status and API error code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "error": {"code": code, "message": message},
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register exception handlers that produce the standard envelope."""

    @app.exception_handler(APIError)
    async def api_error_handler(
        request: Request,
        exc: APIError,
    ) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(MealNotFoundError)
    async def meal_not_found_handler(
        request: Request,
        exc: MealNotFoundError,
    ) -> JSONResponse:
        return _error_response(404, "MEAL_NOT_FOUND", str(exc))

    @app.exception_handler(FoodNotFoundError)
    async def food_not_found_handler(
        request: Request,
        exc: FoodNotFoundError,
    ) -> JSONResponse:
        return _error_response(404, "FOOD_NOT_FOUND", str(exc))

    @app.exception_handler(UnsupportedFoodError)
    async def unsupported_food_handler(
        request: Request,
        exc: UnsupportedFoodError,
    ) -> JSONResponse:
        return _error_response(404, "FOOD_NOT_FOUND", str(exc))

    @app.exception_handler(NutritionUnavailableError)
    async def nutrition_unavailable_handler(
        request: Request,
        exc: NutritionUnavailableError,
    ) -> JSONResponse:
        return _error_response(503, "NUTRITION_UNAVAILABLE", str(exc))

    @app.exception_handler(ValueError)
    async def business_rule_handler(
        request: Request,
        exc: ValueError,
    ) -> JSONResponse:
        return _error_response(409, "INVALID_REQUEST", str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        message = f"Validation failed: {first.get('msg', 'invalid input')}"
        return _error_response(422, "VALIDATION_ERROR", message)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logging.getLogger(__name__).exception(
            "Unhandled error on %s %s",
            request.method,
            request.url.path,
        )
        return _error_response(500, "INTERNAL_ERROR", "Unexpected server error")
