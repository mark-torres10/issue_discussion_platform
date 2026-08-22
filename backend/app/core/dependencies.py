from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.csrf import validate_csrf_token
from app.models.errors import ApiError
from app.services.capability import (
    CAPABILITY_COOKIE_NAME,
    IDEMPOTENCY_HEADER_NAME,
    load_capability_payload,
)
from app.services.sessions import CapabilityContext, StudyApiError


class StudyApiErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except StudyApiError as exc:
            request_id = getattr(request.state, "request_id", "")
            return JSONResponse(
                status_code=exc.status_code,
                content=ApiError(
                    request_id=request_id,
                    error_code=exc.error_code,
                    message=exc.message,
                    retryable=exc.retryable,
                    current_version=exc.current_version,
                    session_status=exc.session_status,
                ).model_dump(),
            )


def register_study_api_error_handler(app: FastAPI) -> None:
    app.add_middleware(StudyApiErrorMiddleware)


def study_error_response(request: Request, exc: StudyApiError) -> ApiError:
    request_id = getattr(request.state, "request_id", "")
    return ApiError(
        request_id=request_id,
        error_code=exc.error_code,
        message=exc.message,
        retryable=exc.retryable,
        current_version=exc.current_version,
        session_status=exc.session_status,
    )


def get_capability(request: Request) -> CapabilityContext:
    signed = request.cookies.get(CAPABILITY_COOKIE_NAME)
    if not signed:
        raise StudyApiError(
            status_code=401,
            error_code="capability_missing",
            message="Participant capability cookie is required",
        )
    try:
        payload = load_capability_payload(signed)
    except Exception:
        raise StudyApiError(
            status_code=401,
            error_code="capability_invalid",
            message="Participant capability is invalid",
        ) from None

    session_id = UUID(payload["session_id"])
    writer_role = payload["writer_role"]
    if writer_role not in ("writer", "read_only"):
        raise StudyApiError(
            status_code=401,
            error_code="capability_invalid",
            message="Participant capability is invalid",
        )
    return CapabilityContext(
        session_id=session_id,
        capability_id=payload["capability_id"],
        writer_role=writer_role,  # type: ignore[arg-type]
        csrf_token=payload["csrf_token"],
    )


def require_csrf(
    request: Request,
    capability: Annotated[CapabilityContext, Depends(get_capability)],
) -> CapabilityContext:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not validate_csrf_token(request, capability.csrf_token):
            raise StudyApiError(
                status_code=403,
                error_code="csrf_rejected",
                message="CSRF token is missing or invalid",
            )
    return capability


def require_idempotency_key(request: Request) -> str:
    key = request.headers.get(IDEMPOTENCY_HEADER_NAME)
    if not key:
        raise StudyApiError(
            status_code=400,
            error_code="validation_error",
            message="Idempotency-Key header is required",
        )
    return key


CapabilityDep = Annotated[CapabilityContext, Depends(get_capability)]
ProtectedCapabilityDep = Annotated[CapabilityContext, Depends(require_csrf)]
IdempotencyKeyDep = Annotated[str, Depends(require_idempotency_key)]
