import concurrent.futures
from datetime import datetime, timedelta

import pytest

from app.services import sessions as sessions_module
from tests.conftest import COMPLETE_PATH, auth_headers, exchange_invitation, start_session


@pytest.mark.parametrize("storage_mode", ["memory", "postgres"], indirect=True)
class TestWriterLease:
    def test_stale_writer_gets_409(
        self, storage_client, invitation_token, storage_mode, monkeypatch
    ) -> None:
        exchange = exchange_invitation(storage_client, invitation_token)
        started = start_session(storage_client, exchange)
        assert started.status_code == 200

        started_at = datetime.fromisoformat(
            started.json()["session"]["started_at"].replace("Z", "+00:00")
        )
        monkeypatch.setattr(
            sessions_module,
            "utc_now",
            lambda: started_at
            + sessions_module.WRITER_LEASE_DURATION
            + timedelta(seconds=1),
        )

        response = storage_client.post(
            COMPLETE_PATH,
            headers=auth_headers(exchange.csrf_token, "stale-writer"),
            cookies=exchange.cookies,
            json={
                "reason": "participant_ended",
                "expected_version": started.json()["session"]["version"],
            },
        )

        assert response.status_code == 409
        assert response.json()["error_code"] == "writer_conflict"


@pytest.mark.parametrize("storage_mode", ["memory", "postgres"], indirect=True)
class TestCompletionRace:
    def test_double_complete_single_transition(
        self, storage_client, invitation_token, storage_mode
    ) -> None:
        exchange = exchange_invitation(storage_client, invitation_token)
        started = start_session(storage_client, exchange)
        version = started.json()["session"]["version"]
        payload = {"reason": "participant_ended", "expected_version": version}

        def complete_once(key: str) -> int:
            response = storage_client.post(
                COMPLETE_PATH,
                headers=auth_headers(exchange.csrf_token, key),
                cookies=exchange.cookies,
                json=payload,
            )
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(complete_once, ["race-a", "race-b"]))

        assert sorted(results) == [200, 409]
        session_read = storage_client.get(
            "/v1/participant-session", cookies=exchange.cookies
        )
        assert session_read.status_code == 200
        assert session_read.json()["status"] == "completed"
