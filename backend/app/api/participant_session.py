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
