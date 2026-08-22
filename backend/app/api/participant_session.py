"""Participant session lifecycle routes.

Read and mutate an authenticated participant session: consent, start, pause,
completion, transcript access, and writer-lease transfer.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import (
    CapabilityDep,
    IdempotencyKeyDep,
    ProtectedCapabilityDep,
    study_error_response,
)
from app.models.session import (
    ConsentRecordRequest,
    ParticipantSessionView,
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionPauseRequest,
    SessionStartRequest,
    SessionStartResponse,
    WriterLeaseTransferRequest,
)
from app.models.transcript import TranscriptResponse
from app.services.sessions import StudyApiError
from app.services.sessions import (
    complete_session,
    get_session_view,
    get_transcript,
    pause_session,
    record_consent,
    start_session,
    transfer_writer_lease,
)
from app.services.transcripts import request_hash

router = APIRouter(prefix="/v1/participant-session", tags=["participant-session"])


@router.get("", response_model=ParticipantSessionView)
def read_participant_session(
    request: Request, capability: CapabilityDep
) -> ParticipantSessionView | JSONResponse:
    """Return the current participant session view.

  Requires a valid ``participant_capability`` cookie. Does not require CSRF
  validation because this route is read-only.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability resolved from the cookie.

  Returns
  -------
  ParticipantSessionView or JSONResponse
      Projected session state on success, or a JSON error body when the
      capability is missing, invalid, or the session cannot be loaded.
  """
    try:
        return get_session_view(capability)
    except StudyApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=study_error_response(request, exc).model_dump(),
        )


@router.post("/consent", response_model=ParticipantSessionView)
def post_consent(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: ConsentRecordRequest,
    idempotency_key: IdempotencyKeyDep,
) -> ParticipantSessionView | JSONResponse:
    """Record participant consent for the session.

  Requires a valid capability cookie, a matching ``X-CSRF-Token`` header, and
  an ``Idempotency-Key`` header. Replays with the same idempotency key return
  the original result without duplicating side effects.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability with CSRF validation applied.
  body : ConsentRecordRequest
      Consent choices and metadata to persist.
  idempotency_key : str
      Client-supplied idempotency key from the ``Idempotency-Key`` header.

  Returns
  -------
  ParticipantSessionView or JSONResponse
      Updated session view on success, or a JSON error body when validation,
      authorization, or persistence fails.
  """
    try:
        return record_consent(
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


@router.post("/start", response_model=SessionStartResponse)
def post_start(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: SessionStartRequest,
    idempotency_key: IdempotencyKeyDep,
) -> SessionStartResponse | JSONResponse:
    """Start the participant session after consent.

  Requires a valid capability cookie, CSRF header, and idempotency key.
  Typically transitions the session from a consented state into active
  interaction.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability with CSRF validation applied.
  body : SessionStartRequest
      Start parameters such as interaction mode.
  idempotency_key : str
      Client-supplied idempotency key from the ``Idempotency-Key`` header.

  Returns
  -------
  SessionStartResponse or JSONResponse
      Start outcome and updated session metadata on success, or a JSON error
      body when the session cannot be started.
  """
    try:
        return start_session(
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


@router.get("/transcript", response_model=TranscriptResponse)
def read_transcript(
    request: Request, capability: CapabilityDep
) -> TranscriptResponse | JSONResponse:
    """Return the session transcript for the authenticated participant.

  Requires a valid ``participant_capability`` cookie. Does not require CSRF
  validation because this route is read-only.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability resolved from the cookie.

  Returns
  -------
  TranscriptResponse or JSONResponse
      Transcript items on success, or a JSON error body when the capability
      is invalid or the transcript is unavailable.
  """
    try:
        return get_transcript(capability)
    except StudyApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=study_error_response(request, exc).model_dump(),
        )


@router.post("/complete", response_model=SessionCompleteResponse)
def post_complete(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: SessionCompleteRequest,
    idempotency_key: IdempotencyKeyDep,
) -> SessionCompleteResponse | JSONResponse:
    """Mark the participant session as complete.

  Requires a valid capability cookie, CSRF header, and idempotency key.
  Finalizes the session and returns completion metadata.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability with CSRF validation applied.
  body : SessionCompleteRequest
      Completion reason and client metadata.
  idempotency_key : str
      Client-supplied idempotency key from the ``Idempotency-Key`` header.

  Returns
  -------
  SessionCompleteResponse or JSONResponse
      Completion outcome on success, or a JSON error body when the session
      cannot be completed.
  """
    try:
        return complete_session(
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


@router.post("/pause", response_model=ParticipantSessionView)
def post_pause(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: SessionPauseRequest,
    idempotency_key: IdempotencyKeyDep,
) -> ParticipantSessionView | JSONResponse:
    """Pause an in-progress participant session.

  Requires a valid capability cookie, CSRF header, and idempotency key.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability with CSRF validation applied.
  body : SessionPauseRequest
      Pause reason and client metadata.
  idempotency_key : str
      Client-supplied idempotency key from the ``Idempotency-Key`` header.

  Returns
  -------
  ParticipantSessionView or JSONResponse
      Updated session view on success, or a JSON error body when the session
      cannot be paused.
  """
    try:
        return pause_session(
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


@router.post("/writer-lease/transfer", response_model=ParticipantSessionView)
def post_writer_lease_transfer(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: WriterLeaseTransferRequest,
    idempotency_key: IdempotencyKeyDep,
) -> ParticipantSessionView | JSONResponse:
    """Transfer the writer lease to another participant device or role.

  Requires a valid capability cookie, CSRF header, and idempotency key.
  On success the caller's capability may change writer role; clients should
  re-read session state after a transfer.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  capability : CapabilityContext
      Authenticated participant capability with CSRF validation applied.
  body : WriterLeaseTransferRequest
      Target device or lease parameters for the transfer.
  idempotency_key : str
      Client-supplied idempotency key from the ``Idempotency-Key`` header.

  Returns
  -------
  ParticipantSessionView or JSONResponse
      Updated session view on success, or a JSON error body when the lease
      cannot be transferred.
  """
    try:
        return transfer_writer_lease(
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
