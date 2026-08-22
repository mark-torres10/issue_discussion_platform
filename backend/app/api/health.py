"""Health and readiness probes.

Liveness (`GET /health`) reports that the process is running.

Readiness (`GET /ready`) reports whether the process can serve its configured role.
In sample contracts mode (`STORAGE_MODE=memory`), readiness is ok without Postgres.
In durable mode (`STORAGE_MODE=postgres`), readiness requires `DATABASE_URL` to be set;
when it is missing, the endpoint returns HTTP 503 with `status` `degraded`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    commit: str | None = None


class ReadyResponse(BaseModel):
    status: str
    reason: str | None = None


SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
def health(settings: SettingsDep) -> HealthResponse:
    """Report process liveness for load balancers and orchestrators.

  No authentication is required. Does not check downstream dependencies.

  Parameters
  ----------
  settings : Settings
      Application settings (used to include the deployed git commit SHA when
      available).

  Returns
  -------
  HealthResponse
      ``status`` ``ok`` and optional ``commit`` identifier.
  """
    return HealthResponse(status="ok", commit=settings.railway_git_commit_sha)


@router.get("/ready", response_model_exclude_none=True)
def ready(settings: SettingsDep, response: Response) -> ReadyResponse:
    """Report whether the service is ready to handle Study API traffic.

  No authentication is required. When ``STORAGE_MODE`` is ``postgres`` and
  ``DATABASE_URL`` is unset, sets the HTTP response status to 503 and returns
  ``status`` ``degraded`` with a reason string.

  Parameters
  ----------
  settings : Settings
      Application settings used to evaluate storage configuration.
  response : Response
      Outgoing HTTP response; may receive status code 503 when not ready.

  Returns
  -------
  ReadyResponse
      ``status`` ``ok`` when ready, or ``degraded`` with a ``reason`` when
      required configuration is missing.
  """
    if settings.storage_mode == "postgres" and not settings.database_url:
        response.status_code = 503
        return ReadyResponse(
            status="degraded",
            reason="DATABASE_URL is required when STORAGE_MODE=postgres",
        )
    return ReadyResponse(status="ok")
