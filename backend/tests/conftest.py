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
from app.services.generation import reset_memory_generation_operations
from app.services.realtime import reset_memory_realtime_state
from app.services.sessions import reset_postgres_ephemeral_state, reset_store, seed_postgres_invitation

MOCK_AI_TEXT = (
    "That is a fair concern. If a speaker spreads ideas that make some students "
    "feel unsafe, how should a university decide when speech crosses that line?"
)

EXCHANGE_PATH = "/v1/participant-access/exchange"
SESSION_PATH = "/v1/participant-session"
MESSAGES_PATH = "/v1/participant-session/messages"
TRANSCRIPT_PATH = "/v1/participant-session/transcript"
START_PATH = "/v1/participant-session/start"
COMPLETE_PATH = "/v1/participant-session/complete"
OBSERVATIONS_PATH = "/v1/participant-session/observations"
REALTIME_PATH = "/v1/participant-session/realtime/calls"
INTERNAL_REALTIME_ITEMS_PATH = "/internal/v1/realtime/calls/{openai_call_id}/items"
WORKER_TOKEN = "test-token"

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260822100000_study_core_schema.sql"
)
GENERATION_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260822110000_generation_operations.sql"
)
REALTIME_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260822120000_realtime_calls.sql"
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

    def table_exists(table_name: str) -> bool:
        result = subprocess.run(
            [
                "psql",
                postgres_database_url,
                "-tAc",
                f"SELECT to_regclass('public.{table_name}') IS NOT NULL",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() == "t"

    if not table_exists("sessions"):
        subprocess.run(
            ["psql", postgres_database_url, "-v", "ON_ERROR_STOP=1", "-f", str(MIGRATION_PATH)],
            check=True,
            capture_output=True,
            text=True,
        )

    if not table_exists("generation_operations"):
        subprocess.run(
            [
                "psql",
                postgres_database_url,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(GENERATION_MIGRATION_PATH),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    if not table_exists("realtime_calls"):
        subprocess.run(
            [
                "psql",
                postgres_database_url,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(REALTIME_MIGRATION_PATH),
            ],
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
def client(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch, mock_openai_realtime
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.setenv("OPENAI_API_KEY", "mock")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_store()
    reset_memory_generation_operations()
    reset_memory_realtime_state()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_openai_client(monkeypatch: pytest.MonkeyPatch):
    from types import SimpleNamespace

    from app.integrations import openai_client

    class MockChatCompletions:
        call_count = 0

        def create(self, **kwargs: object) -> SimpleNamespace:
            MockChatCompletions.call_count += 1
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=MOCK_AI_TEXT)),
                ]
            )

    class MockOpenAIClient:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(completions=MockChatCompletions())

    MockChatCompletions.call_count = 0
    client = MockOpenAIClient()
    monkeypatch.setenv("OPENAI_API_KEY", "mock")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")
    openai_client.set_openai_client_factory(lambda: client)  # type: ignore[return-value]
    yield client
    openai_client.set_openai_client_factory(None)


@pytest.fixture(params=["memory", "postgres"])
def storage_mode(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    mode = request.param
    if mode == "postgres" and not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; skipping postgres contract tests")
    monkeypatch.setenv("STORAGE_MODE", mode)
    reset_engine()
    reset_postgres_ephemeral_state()
    if mode == "postgres":
        monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        reset_store()
    return mode


@pytest.fixture
def invitation_token(storage_mode: str) -> str:
    if storage_mode == "postgres":
        return f"postgres-contract-invitation-{uuid4()}-minimum-length"
    return SAMPLE_WRITER_INVITATION_TOKEN


@pytest.fixture
def storage_client(
    app: FastAPI,
    storage_mode: str,
    invitation_token: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    if storage_mode == "postgres":
        import asyncio

        asyncio.run(seed_postgres_invitation(invitation_token))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def memory_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "memory")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_store()


@pytest.fixture
def postgres_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_MODE", "postgres")
    if os.environ.get("DATABASE_URL"):
        monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])


@pytest.fixture
def commit_sha(monkeypatch: pytest.MonkeyPatch) -> str:
    sha = "abc123def456"
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", sha)
    return sha


def exchange_invitation(
    client: TestClient,
    token: str | None = None,
) -> ExchangeResult:
    invitation_token = token or SAMPLE_WRITER_INVITATION_TOKEN
    response = client.post(EXCHANGE_PATH, json={"invitation_token": invitation_token})
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


def worker_auth_headers() -> dict[str, str]:
    return {"X-Worker-Token": WORKER_TOKEN}


@pytest.fixture
def worker_token_env(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("INTERNAL_WORKER_TOKEN", WORKER_TOKEN)
    return WORKER_TOKEN


@pytest.fixture
def mock_openai_realtime(monkeypatch: pytest.MonkeyPatch):
    from app.integrations import openai_realtime

    class MockRealtimeClient:
        call_count = 0

        def create_call(
            self,
            *,
            sdp_offer: str,
            session_config: dict[str, object],
            safety_identifier: str,
        ) -> openai_realtime.RealtimeCallResult:
            MockRealtimeClient.call_count += 1
            call_id = f"rtc_mock_{MockRealtimeClient.call_count}"
            return openai_realtime.RealtimeCallResult(
                sdp_answer="v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=mock-realtime\r\n",
                openai_call_id=call_id,
                location_header=f"/v1/realtime/calls/{call_id}",
            )

    MockRealtimeClient.call_count = 0
    client = MockRealtimeClient()
    openai_realtime.set_realtime_client_factory(lambda: client)
    yield client
    openai_realtime.set_realtime_client_factory(None)


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
