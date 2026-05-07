from http import HTTPStatus
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import ApiErrorResponse, ApiResponse


def api_success(data: Any = None, *, message: str | None = None, meta: dict | None = None) -> ApiResponse:
    return ApiResponse(message=message, data=data, meta=meta or {})


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    message = _error_message(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiErrorResponse(
            error={
                "code": _error_code(message=message, status_code=exc.status_code),
                "message": message,
                "details": _error_details(exc.detail),
            }
        ).model_dump(mode="json", exclude_none=True),
        headers=exc.headers,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ApiErrorResponse(
            error={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": _validation_details(exc.errors()),
            }
        ).model_dump(mode="json", exclude_none=True),
    )


def _error_message(detail: Any) -> str:
    if isinstance(detail, dict):
        value = detail.get("message") or detail.get("detail")
        if value:
            return str(value)
    if isinstance(detail, str):
        return detail
    return "Unexpected API error"


def _error_details(detail: Any) -> Any | None:
    if isinstance(detail, dict):
        return detail.get("details")
    return None


def _error_code(*, message: str, status_code: int) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in message.upper()).strip("_")
    normalized = "_".join(part for part in normalized.split("_") if part)
    if normalized:
        return normalized[:80]
    try:
        return HTTPStatus(status_code).phrase.upper().replace(" ", "_")
    except ValueError:
        return "API_ERROR"


def _validation_details(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        item: dict[str, Any] = {}
        for key, value in error.items():
            if key == "ctx" and isinstance(value, dict):
                item[key] = {ctx_key: str(ctx_value) for ctx_key, ctx_value in value.items()}
            else:
                item[key] = value
        sanitized.append(item)
    return sanitized
