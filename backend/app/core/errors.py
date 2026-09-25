"""RFC-7807-style error handling.

Every error response returned by the API has the shape:
    {"type": "<url or short code>", "title": "<human title>", "detail": "<human detail>", "code": "<machine code>"}
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class ApiError(Exception):
    """Raise this anywhere in the app for a structured, RFC-7807-style error."""

    def __init__(
        self,
        code: str,
        title: str,
        detail: str = "",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        type_: str = "about:blank",
    ) -> None:
        self.code = code
        self.title = title
        self.detail = detail
        self.status_code = status_code
        self.type_ = type_
        super().__init__(detail or title)


def _problem(
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    code: str,
    type_: str = "about:blank",
) -> JSONResponse:
    logger.warning(
        "api_error",
        path=str(request.url.path),
        status_code=status_code,
        code=code,
        title=title,
        detail=detail,
    )
    return JSONResponse(
        status_code=status_code,
        content={"type": type_, "title": title, "detail": detail, "code": code},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return _problem(request, exc.status_code, exc.title, exc.detail, exc.code, exc.type_)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _problem(
            request,
            exc.status_code,
            title=_status_title(exc.status_code),
            detail=detail,
            code=f"http_{exc.status_code}",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation error",
            detail=str(exc.errors()),
            code="validation_error",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", path=str(request.url.path))
        return _problem(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Internal server error",
            detail="An unexpected error occurred. Please try again.",
            code="internal_error",
        )


def _status_title(status_code: int) -> str:
    titles = {
        400: "Bad request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not found",
        409: "Conflict",
        422: "Unprocessable entity",
        429: "Too many requests",
        500: "Internal server error",
        501: "Not implemented",
        503: "Service unavailable",
    }
    return titles.get(status_code, "Error")
