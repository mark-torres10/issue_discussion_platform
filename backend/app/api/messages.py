"""Participant message creation routes.

Appends user or assistant messages to the session transcript during an active
participant session.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import (
    IdempotencyKeyDep,
    ProtectedCapabilityDep,
    study_error_response,
)
from app.models.transcript import MessageCreate, MessageResponse
from app.services.generation import create_message
from app.services.sessions import StudyApiError
from app.services.transcripts import request_hash

router = APIRouter(prefix="/v1/participant-session", tags=["participant-messages"])


@router.post("/messages", response_model=MessageResponse)
def post_message(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: MessageCreate,
    idempotency_key: IdempotencyKeyDep,
) -> MessageResponse | JSONResponse:
    """Create a transcript message and optionally trigger assistant generation.

  Requires a valid ``participant_capability`` cookie, a matching
  ``X-CSRF-Token`` header, and an ``Idempotency-Key`` header. The caller
  must hold the writer role for mutating transcript content.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability with CSRF validation applied.
  body : MessageCreate
      Message content and generation options.
  idempotency_key : str
      Client-supplied idempotency key from the ``Idempotency-Key`` header.

  Returns
  -------
  MessageResponse or JSONResponse
      Created message (and any generation metadata) on success, or a JSON
      error body when validation, authorization, or persistence fails.
  """
    try:
        return create_message(
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
