import os
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import api_router
from app.core.errors import register_exception_handlers, register_middleware
from app.models.enums import FrozenModel


class SampleInput(FrozenModel):
    name: str


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI(title="Issue Discussion Platform API")
    register_middleware(application)
    register_exception_handlers(application)
    application.include_router(api_router)

    @application.post("/_test/validation")
    def _test_validation(body: SampleInput) -> dict[str, bool]:
        return {"ok": True}

    return application


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def postgres_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "postgres")
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.fixture
def memory_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.delenv("DATABASE_URL", raising=False)


@pytest.fixture
def commit_sha(monkeypatch: pytest.MonkeyPatch) -> str:
    sha = "abc123def456"
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", sha)
    return sha
