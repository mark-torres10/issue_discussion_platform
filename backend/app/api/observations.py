from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import (
    IdempotencyKeyDep,
    ProtectedCapabilityDep,
    study_error_response,
)
from app.models.observations import ObservationBatchCreate, ObservationBatchResponse
from app.services.sessions import StudyApiError, record_observations
from app.services.transcripts import request_hash

router = APIRouter(prefix="/v1/participant-session", tags=["participant-observations"])


@router.post("/observations", response_model=ObservationBatchResponse)
def post_observations(
    request: Request,
    capability: ProtectedCapabilityDep,
    body: ObservationBatchCreate,
    idempotency_key: IdempotencyKeyDep,
) -> ObservationBatchResponse | JSONResponse:
    try:
        return record_observations(
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
