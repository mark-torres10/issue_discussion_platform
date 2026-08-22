from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import (
    IdempotencyKeyDep,
    ProtectedCapabilityDep,
    study_error_response,
)
from app.models.transcript import MessageCreate, MessageResponse
from app.services.sessions import StudyApiError, create_message
from app.services.transcripts import request_hash

router = APIRouter(prefix="/v1/participant-session", tags=["participant-messages"])


@router.post("/messages", response_model=MessageResponse)
def post_message(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: MessageCreate,
    idempotency_key: IdempotencyKeyDep,
) -> MessageResponse | JSONResponse:
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
