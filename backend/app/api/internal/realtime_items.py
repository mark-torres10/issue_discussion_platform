import os

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import study_error_response
from app.models.realtime import (
    RealtimeProviderItemIngest,
    RealtimeProviderItemIngestResponse,
)
from app.services.realtime import ingest_provider_item
from app.services.sessions import StudyApiError

router = APIRouter(prefix="/internal/v1/realtime", tags=["internal-realtime"])


def _require_worker_token(x_worker_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get("INTERNAL_WORKER_TOKEN")
    if not expected or x_worker_token != expected:
        raise StudyApiError(
            status_code=401,
            error_code="staff_forbidden",
            message="Worker authentication required",
        )


@router.post(
    "/calls/{openai_call_id}/items",
    response_model=RealtimeProviderItemIngestResponse,
)
def post_realtime_provider_item(
    request: Request,
    openai_call_id: str,
    body: RealtimeProviderItemIngest,
    x_worker_token: str | None = Header(default=None),
) -> RealtimeProviderItemIngestResponse | JSONResponse:
    try:
        _require_worker_token(x_worker_token)
        return ingest_provider_item(openai_call_id, body)
    except StudyApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=study_error_response(request, exc).model_dump(),
        )
