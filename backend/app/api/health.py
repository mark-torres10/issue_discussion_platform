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
    return HealthResponse(status="ok", commit=settings.railway_git_commit_sha)


@router.get("/ready", response_model_exclude_none=True)
def ready(settings: SettingsDep, response: Response) -> ReadyResponse:
    if settings.storage_mode == "postgres" and not settings.database_url:
        response.status_code = 503
        return ReadyResponse(
            status="degraded",
            reason="DATABASE_URL is required when STORAGE_MODE=postgres",
        )
    return ReadyResponse(status="ok")
