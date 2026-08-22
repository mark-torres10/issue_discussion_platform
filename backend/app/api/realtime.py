from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import (
    IdempotencyKeyDep,
    ProtectedCapabilityDep,
    study_error_response,
)
from app.models.realtime import RealtimeCallCreateRequest, RealtimeCallCreateResponse
from app.services.sessions import StudyApiError, create_realtime_call
from app.services.transcripts import request_hash

router = APIRouter(prefix="/v1/participant-session", tags=["participant-realtime"])


@router.post("/realtime/calls", response_model=RealtimeCallCreateResponse)
def post_realtime_call(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: RealtimeCallCreateRequest,
    idempotency_key: IdempotencyKeyDep,
) -> RealtimeCallCreateResponse | JSONResponse:
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
