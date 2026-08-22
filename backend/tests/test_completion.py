from datetime import UTC, datetime

import pytest

from app.services import sessions as sessions_module
from tests.conftest import (
    COMPLETE_PATH,
    SESSION_PATH,
    TRANSCRIPT_PATH,
    auth_headers,
    exchange_invitation,
    post_message,
    start_session,
)


@pytest.mark.parametrize("storage_mode", ["memory", "postgres"], indirect=True)
class TestCompletion:
    def test_complete_is_idempotent(
        self, storage_client, invitation_token, storage_mode
    ) -> None:
        exchange = exchange_invitation(storage_client, invitation_token)
        started = start_session(storage_client, exchange)
        version = started.json()["session"]["version"]
        headers = auth_headers(exchange.csrf_token, "complete-1")
        payload = {"reason": "participant_ended", "expected_version": version}

        first = storage_client.post(
            COMPLETE_PATH,
            headers=headers,
            cookies=exchange.cookies,
            json=payload,
        )
        second = storage_client.post(
            COMPLETE_PATH,
            headers=headers,
            cookies=exchange.cookies,
            json=payload,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()
        assert first.json()["session"]["status"] == "completed"

    def test_completed_session_blocks_new_messages(
        self, storage_client, invitation_token, storage_mode
    ) -> None:
        exchange = exchange_invitation(storage_client, invitation_token)
        started = start_session(storage_client, exchange)
        version = started.json()["session"]["version"]
        storage_client.post(
            COMPLETE_PATH,
            headers=auth_headers(exchange.csrf_token, "complete-block"),
            cookies=exchange.cookies,
            json={"reason": "participant_ended", "expected_version": version},
        )

        blocked = post_message(
            storage_client,
            exchange,
            text="Too late",
            expected_version=version + 1,
            idempotency_key="msg-after-complete",
        )

        assert blocked.status_code == 409
        assert blocked.json()["error_code"] == "session_already_completed"

    def test_grace_read_after_complete(
        self, storage_client, invitation_token, storage_mode
    ) -> None:
        exchange = exchange_invitation(storage_client, invitation_token)
        started = start_session(storage_client, exchange)
        version = started.json()["session"]["version"]
        storage_client.post(
            COMPLETE_PATH,
            headers=auth_headers(exchange.csrf_token, "complete-read"),
            cookies=exchange.cookies,
            json={"reason": "participant_ended", "expected_version": version},
        )

        session_read = storage_client.get(SESSION_PATH, cookies=exchange.cookies)
        transcript_read = storage_client.get(TRANSCRIPT_PATH, cookies=exchange.cookies)

        assert session_read.status_code == 200
        assert session_read.json()["status"] == "completed"
        assert transcript_read.status_code == 200

    def test_writes_blocked_after_grace_period(
        self, storage_client, invitation_token, storage_mode, monkeypatch
    ) -> None:
        exchange = exchange_invitation(storage_client, invitation_token)
        started = start_session(storage_client, exchange)
        version = started.json()["session"]["version"]
        storage_client.post(
            COMPLETE_PATH,
            headers=auth_headers(exchange.csrf_token, "complete-grace"),
            cookies=exchange.cookies,
            json={"reason": "participant_ended", "expected_version": version},
        )

        past_grace = datetime(2099, 1, 1, tzinfo=UTC)
        monkeypatch.setattr(sessions_module, "utc_now", lambda: past_grace)

        blocked = post_message(
            storage_client,
            exchange,
            text="After grace",
            expected_version=version + 1,
            idempotency_key="msg-grace",
        )

        assert blocked.status_code == 410
        assert blocked.json()["error_code"] == "session_unavailable"
