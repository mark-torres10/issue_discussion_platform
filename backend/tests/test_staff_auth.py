import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.capability import CAPABILITY_COOKIE_NAME, sign_capability_payload
STAFF_MEMBERSHIP_MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260822140000_staff_membership.sql"
)
TEST_JWT_SECRET = "test-supabase-jwt-secret-for-step8"
EXPORT_PATH = "/v1/staff/sessions/{session_id}/export"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_test_jwt(*, sub: str, expires_in_seconds: int = 3600) -> str:
    header = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    payload = _b64url_encode(
        json.dumps(
            {
                "sub": sub,
                "role": "authenticated",
                "exp": int(time.time()) + expires_in_seconds,
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(
        TEST_JWT_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header}.{payload}.{_b64url_encode(signature)}"


def staff_auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def apply_staff_membership_schema(postgres_database_url: str) -> None:
    import subprocess

    result = subprocess.run(
        [
            "psql",
            postgres_database_url,
            "-tAc",
            "SELECT to_regclass('public.staff_membership') IS NOT NULL",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout.strip() != "t":
        subprocess.run(
            [
                "psql",
                postgres_database_url,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(STAFF_MEMBERSHIP_MIGRATION_PATH),
            ],
            check=True,
            capture_output=True,
            text=True,
        )


@pytest.fixture
def staff_jwt_env(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    return TEST_JWT_SECRET


class TestJwtVerifier:
    def test_rejects_missing_authorization(
        self,
        app,
        postgres_database_url,
        apply_staff_membership_schema,
        monkeypatch: pytest.MonkeyPatch,
        staff_jwt_env: str,
    ) -> None:
        monkeypatch.setenv("STORAGE_MODE", "postgres")
        monkeypatch.setenv("DATABASE_URL", postgres_database_url)
        from app.core.config import get_settings

        get_settings.cache_clear()

        with TestClient(app) as client:
            response = client.get(
                EXPORT_PATH.format(session_id="018f5a20-7c3a-7000-8000-000000000001")
            )

        assert response.status_code == 401
        assert response.json()["error_code"] == "staff_auth_required"

    def test_rejects_participant_cookie(
        self,
        app,
        postgres_database_url,
        apply_staff_membership_schema,
        monkeypatch: pytest.MonkeyPatch,
        staff_jwt_env: str,
    ) -> None:
        monkeypatch.setenv("STORAGE_MODE", "postgres")
        monkeypatch.setenv("DATABASE_URL", postgres_database_url)
        from app.core.config import get_settings

        get_settings.cache_clear()

        signed = sign_capability_payload(
            {
                "session_id": "018f5a20-7c3a-7000-8000-000000000001",
                "capability_id": "cap-1",
                "writer_role": "writer",
                "csrf_token": "csrf-token",
            }
        )

        with TestClient(app) as client:
            response = client.get(
                EXPORT_PATH.format(session_id="018f5a20-7c3a-7000-8000-000000000001"),
                cookies={CAPABILITY_COOKIE_NAME: signed},
            )

        assert response.status_code in {401, 403}
        assert response.json()["error_code"] in {
            "staff_auth_required",
            "staff_forbidden",
        }
