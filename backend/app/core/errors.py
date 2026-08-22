"""Request correlation and centralized API error responses.

Assigns a per-request ID for tracing and registers exception handlers that map
validation failures, domain errors, and unexpected exceptions to structured
:class:`~app.models.errors.ApiError` JSON payloads.
"""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.models.errors import ApiError
from app.services.sessions import StudyApiError


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a unique request ID before downstream handlers run.

    Stores the ID on ``request.state.request_id`` so error responses and logs
    can correlate a single client request.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid.uuid4())
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Attach request correlation middleware to a FastAPI application.

    Parameters
    ----------
    app : fastapi.FastAPI
        Application that should receive a ``request_id`` on every request.
    """
    app.add_middleware(RequestIdMiddleware)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def register_exception_handlers(app: FastAPI) -> None:
    """Register JSON exception handlers for API errors.

    Maps request validation failures, :class:`~app.services.sessions.StudyApiError`,
    and uncaught exceptions to :class:`~app.models.errors.ApiError` responses
    that include the request correlation ID.

    Parameters
    ----------
    app : fastapi.FastAPI
        Application whose errors should be returned in the Study API envelope.
    """
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ApiError(
                request_id=_request_id(request),
                error_code="validation_error",
                message="Request validation failed",
                retryable=False,
            ).model_dump(),
        )

    @app.exception_handler(StudyApiError)
    async def study_api_error_handler(
        request: Request, exc: StudyApiError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiError(
                request_id=_request_id(request),
                error_code=exc.error_code,
                message=exc.message,
                retryable=exc.retryable,
                current_version=exc.current_version,
                session_status=exc.session_status,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ApiError(
                request_id=_request_id(request),
                error_code="internal_error",
                message="An internal error occurred",
                retryable=False,
            ).model_dump(),
        )
