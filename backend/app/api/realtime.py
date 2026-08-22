"""Participant realtime call routes.

Creates realtime voice calls for an authenticated participant session.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import (
    IdempotencyKeyDep,
    ProtectedCapabilityDep,
    study_error_response,
)
from app.models.realtime import RealtimeCallCreateRequest, RealtimeCallCreateResponse
from app.services.realtime import create_realtime_call
from app.services.sessions import StudyApiError
from app.services.transcripts import request_hash

router = APIRouter(prefix="/v1/participant-session", tags=["participant-realtime"])


@router.post("/realtime/calls", response_model=RealtimeCallCreateResponse)
def post_realtime_call(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: RealtimeCallCreateRequest,
    idempotency_key: IdempotencyKeyDep,
) -> RealtimeCallCreateResponse | JSONResponse:
    """Create a realtime provider call for the session.

  Requires a valid ``participant_capability`` cookie, a matching
  ``X-CSRF-Token`` header, and an ``Idempotency-Key`` header. Returns
  provider connection details the client uses to join the call.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability with CSRF validation applied.
  body : RealtimeCallCreateRequest
      Realtime call parameters and client metadata.
  idempotency_key : str
      Client-supplied idempotency key from the ``Idempotency-Key`` header.

  Returns
  -------
  RealtimeCallCreateResponse or JSONResponse
      Call identifiers and connection details on success, or a JSON error
      body when validation, authorization, or provider setup fails.
  """
    try:
        return create_realtime_call(
            capability,
            body,
            idempotency_key=idempotency_key,
            request_hash=request_hash(body),
        )
    except StudyApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=study_error_response(request, exc).model_dump(),
        )
