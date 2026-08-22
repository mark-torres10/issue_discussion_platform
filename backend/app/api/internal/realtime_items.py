"""Internal realtime provider item ingestion routes.

Worker-facing endpoints that persist transcript items emitted by the realtime
provider. Not exposed to participant or staff clients.
"""

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
    """Validate the internal worker token from the request header.

  Compares ``X-Worker-Token`` against the ``INTERNAL_WORKER_TOKEN``
  environment variable.

  Parameters
  ----------
  x_worker_token : str or None
      Value of the ``X-Worker-Token`` header, if present.

  Raises
  ------
  StudyApiError
      With HTTP 401 when the token is missing or does not match the
      configured worker secret.
  """
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
    """Ingest a realtime provider transcript item for a call.

  Requires a valid ``X-Worker-Token`` header matching
  ``INTERNAL_WORKER_TOKEN``. Does not use participant cookies or CSRF.
  Idempotent when the provider item identifier was already stored.

  Parameters
  ----------
  request : Request
      Incoming HTTP request (used for structured error responses).
  openai_call_id : str
      Provider call identifier in the URL path.
  body : RealtimeProviderItemIngest
      Provider item payload to persist against the call.
  x_worker_token : str or None
      Worker authentication token from the ``X-Worker-Token`` header.

  Returns
  -------
  RealtimeProviderItemIngestResponse or JSONResponse
      Ingestion outcome on success, or a JSON error body when authentication
      fails or the item cannot be stored.
  """
    try:
        _require_worker_token(x_worker_token)
        return ingest_provider_item(openai_call_id, body)
    except StudyApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=study_error_response(request, exc).model_dump(),
        )
