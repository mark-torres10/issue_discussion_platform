import os
from collections.abc import AsyncIterator, Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.api.router import api_router
from app.core.cors import register_cors
from app.core.dependencies import register_study_api_error_handler
from app.core.errors import register_exception_handlers, register_middleware
from app.db.engine import reset_engine
from app.models.enums import FrozenModel
from app.sample_data.invitations import (
    SAMPLE_WRITER_INVITATION_TOKEN,
    UNKNOWN_INVITATION_TOKEN,
)
from app.services.capability import CSRF_HEADER_NAME, IDEMPOTENCY_HEADER_NAME
from app.services.sessions import reset_store

EXCHANGE_PATH = "/v1/participant-access/exchange"
SESSION_PATH = "/v1/participant-session"
MESSAGES_PATH = "/v1/participant-session/messages"
TRANSCRIPT_PATH = "/v1/participant-session/transcript"
START_PATH = "/v1/participant-session/start"
COMPLETE_PATH = "/v1/participant-session/complete"
OBSERVATIONS_PATH = "/v1/participant-session/observations"
REALTIME_PATH = "/v1/participant-session/realtime/calls"

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260822100000_study_core_schema.sql"
)


class SampleInput(FrozenModel):
    name: str


class ExchangeResult:
    def __init__(
        self,
        *,
        response: Any,
        csrf_token: str,
        cookies: dict[str, str],
        writer_role: str,
    ) -> None:
        self.response = response
        self.csrf_token = csrf_token
        self.cookies = cookies
        self.writer_role = writer_role


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


@pytest.fixture(scope="session")
def postgres_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not set; skipping Postgres repository tests")
    return database_url


@pytest.fixture(scope="session")
def apply_study_schema(postgres_database_url: str) -> None:
    import subprocess

    exists = subprocess.run(
        [
            "psql",
            postgres_database_url,
            "-tAc",
            "SELECT to_regclass('public.sessions') IS NOT NULL",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    if exists.stdout.strip() == "t":
        return

    subprocess.run(
        ["psql", postgres_database_url, "-v", "ON_ERROR_STOP=1", "-f", str(MIGRATION_PATH)],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
async def postgres_engine(postgres_database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        _normalize_database_url(postgres_database_url), pool_pre_ping=True
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(
    postgres_engine: AsyncEngine, apply_study_schema: None
) -> AsyncIterator[AsyncSession]:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def _reset_db_engine_cache() -> Generator[None, None, None]:
    reset_engine()
    yield
    reset_engine()


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI(title="Issue Discussion Platform API")
    register_middleware(application)
    register_exception_handlers(application)
    register_study_api_error_handler(application)
    register_cors(application)
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


@pytest.fixture(autouse=True)
def reset_memory_store(memory_mode: None) -> None:
    reset_store()


@pytest.fixture
def commit_sha(monkeypatch: pytest.MonkeyPatch) -> str:
    sha = "abc123def456"
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", sha)
    return sha


def exchange_invitation(
    client: TestClient,
    token: str = SAMPLE_WRITER_INVITATION_TOKEN,
) -> ExchangeResult:
    response = client.post(EXCHANGE_PATH, json={"invitation_token": token})
    csrf_token = response.headers.get(CSRF_HEADER_NAME, "")
    body = response.json()
    writer_role = body.get("writer_role", "")
    return ExchangeResult(
        response=response,
        csrf_token=csrf_token,
        cookies=dict(response.cookies),
        writer_role=writer_role,
    )


def auth_headers(csrf_token: str, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {CSRF_HEADER_NAME: csrf_token}
    if idempotency_key is not None:
        headers[IDEMPOTENCY_HEADER_NAME] = idempotency_key
    return headers


def start_session(
    client: TestClient,
    exchange: ExchangeResult,
    *,
    expected_version: int = 1,
    idempotency_key: str = "start-1",
) -> Any:
    return client.post(
        START_PATH,
        headers=auth_headers(exchange.csrf_token, idempotency_key),
        cookies=exchange.cookies,
        json={
            "preferred_mode": "text",
            "expected_version": expected_version,
        },
    )


def post_message(
    client: TestClient,
    exchange: ExchangeResult,
    *,
    text: str,
    expected_version: int,
    idempotency_key: str,
    client_message_id: str | None = None,
) -> Any:
    return client.post(
        MESSAGES_PATH,
        headers=auth_headers(exchange.csrf_token, idempotency_key),
        cookies=exchange.cookies,
        json={
            "client_message_id": client_message_id or str(uuid4()),
            "text": text,
            "expected_version": expected_version,
        },
    )
