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
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid.uuid4())
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def register_exception_handlers(app: FastAPI) -> None:
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
