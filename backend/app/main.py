import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Issue Discussion Platform API")


class HealthResponse(BaseModel):
    status: str
    commit: str | None = None


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        commit=os.environ.get("RAILWAY_GIT_COMMIT_SHA"),
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Issue Discussion Platform API"}
