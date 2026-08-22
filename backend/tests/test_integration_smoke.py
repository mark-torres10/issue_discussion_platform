"""Deployed Study API smoke tests.

Set SMOKE_BASE_URL to the public API origin (no trailing slash) to run against
Railway or another environment. Without it, tests skip with a reason.

Optional: SMOKE_INVITATION_TOKEN for postgres-backed deployments. When unset,
the in-memory sample token is used (works only when STORAGE_MODE=memory).
"""

from __future__ import annotations

import os
from collections.abc import Generator

import httpx
import pytest

from app.sample_data.invitations import SAMPLE_WRITER_INVITATION_TOKEN

EXCHANGE_PATH = "/v1/participant-access/exchange"
SESSION_PATH = "/v1/participant-session"


def _smoke_base_url() -> str | None:
    url = os.environ.get("SMOKE_BASE_URL", "").strip().rstrip("/")
    return url or None


@pytest.fixture
def smoke_client() -> Generator[httpx.Client | None, None, None]:
    base = _smoke_base_url()
    if base is None:
        yield None
        return
    with httpx.Client(base_url=base, timeout=30.0, follow_redirects=True) as client:
        yield client


class TestHealthEndpoints:
    def test_health_ok(self, smoke_client: httpx.Client | None) -> None:
        if smoke_client is None:
            pytest.skip("SMOKE_BASE_URL is not set; skipping deployed integration smoke")

        response = smoke_client.get("/health")

        assert response.status_code == 200
        assert response.json().get("status") == "ok"


class TestParticipantSmoke:
    def test_exchange_and_read_session(self, smoke_client: httpx.Client | None) -> None:
        if smoke_client is None:
            pytest.skip("SMOKE_BASE_URL is not set; skipping deployed integration smoke")

        invitation_token = os.environ.get(
            "SMOKE_INVITATION_TOKEN", SAMPLE_WRITER_INVITATION_TOKEN
        )
        exchange_response = smoke_client.post(
            EXCHANGE_PATH,
            json={"invitation_token": invitation_token},
        )
        if exchange_response.status_code == 404:
            pytest.skip(
                "Invitation token not valid on target API; set SMOKE_INVITATION_TOKEN"
            )

        assert exchange_response.status_code == 200
        exchange_body = exchange_response.json()
        assert exchange_body.get("writer_role") in {"writer", "read_only"}

        session_response = smoke_client.get(
            SESSION_PATH,
            cookies=exchange_response.cookies,
        )
        assert session_response.status_code == 200
        session_body = session_response.json()
        assert session_body.get("writer_role") in {"writer", "read_only"}
        assert "status" in session_body
