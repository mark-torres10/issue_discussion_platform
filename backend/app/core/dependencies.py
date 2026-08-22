"""FastAPI dependencies for participant capability auth, CSRF, and idempotency.

Provides dependency callables and type aliases used by participant-facing routes
to load signed capability cookies, enforce CSRF on mutating requests, and
require idempotency keys.
"""

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
from app.core.config import get_settings
from app.services.sessions import CapabilityContext, StudyApiError


def require_postgres_database_url() -> str:
    """Return the configured Postgres URL when durable storage is enabled.

    Returns
    -------
    str
        Value of ``DATABASE_URL``.

    Raises
    ------
    RuntimeError
        If ``STORAGE_MODE`` is not ``postgres`` or ``DATABASE_URL`` is unset.
    """
    settings = get_settings()
    if not settings.use_postgres:
        raise RuntimeError("Postgres storage is not enabled")
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required when STORAGE_MODE=postgres")
    return settings.database_url


class StudyApiErrorMiddleware(BaseHTTPMiddleware):
    """Convert uncaught :class:`~app.services.sessions.StudyApiError` into JSON responses.

    Catches domain errors raised during request handling and serializes them as
    :class:`~app.models.errors.ApiError` payloads with the request correlation ID.
    """

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
    """Attach :class:`StudyApiErrorMiddleware` to a FastAPI application.

    Parameters
    ----------
    app : fastapi.FastAPI
        Application that should return structured errors for
        :class:`~app.services.sessions.StudyApiError`.
    """
    app.add_middleware(StudyApiErrorMiddleware)


def study_error_response(request: Request, exc: StudyApiError) -> ApiError:
    """Build an :class:`~app.models.errors.ApiError` from a domain exception.

    Parameters
    ----------
    request : fastapi.Request
        Current request, used to read the correlation ID from ``request.state``.
    exc : StudyApiError
        Domain error to serialize.

    Returns
    -------
    ApiError
        Structured error payload for the client.
    """
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
    """Load and validate the signed participant capability cookie.

    Parameters
    ----------
    request : fastapi.Request
        Incoming request whose cookies are inspected.

    Returns
    -------
    CapabilityContext
        Session identity, capability ID, writer role, and CSRF token for the
        participant.

    Raises
    ------
    StudyApiError
        With ``capability_missing`` when the cookie is absent, or
        ``capability_invalid`` when the signature, payload, or writer role is
        invalid.
    """
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
    """Require a valid CSRF token on mutating participant requests.

    Parameters
    ----------
    request : fastapi.Request
        Incoming request whose CSRF header is validated.
    capability : CapabilityContext
        Participant capability loaded by :func:`get_capability`.

    Returns
    -------
    CapabilityContext
        The same ``capability`` when validation succeeds or the method is safe.

    Raises
    ------
    StudyApiError
        With ``csrf_rejected`` when a ``POST``, ``PUT``, ``PATCH``, or
        ``DELETE`` request lacks a matching CSRF header.
    """
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not validate_csrf_token(request, capability.csrf_token):
            raise StudyApiError(
                status_code=403,
                error_code="csrf_rejected",
                message="CSRF token is missing or invalid",
            )
    return capability


def require_idempotency_key(request: Request) -> str:
    """Require the ``Idempotency-Key`` header on a request.

    Parameters
    ----------
    request : fastapi.Request
        Incoming request whose headers are inspected.

    Returns
    -------
    str
        The idempotency key supplied by the client.

    Raises
    ------
    StudyApiError
        With ``validation_error`` when the header is missing.
    """
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
