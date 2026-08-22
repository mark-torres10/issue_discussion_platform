from tests.conftest import (
    COMPLETE_PATH,
    REALTIME_PATH,
    auth_headers,
    exchange_invitation,
    start_session,
)


class TestRealtimeSetup:
    def test_response_has_no_call_id(
        self, client, mock_openai_realtime, worker_token_env
    ) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        response = client.post(
            REALTIME_PATH,
            headers=auth_headers(exchange.csrf_token, "rtc-secret-1"),
            cookies=exchange.cookies,
            json={
                "sdp_offer": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\n",
                "expected_version": version,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"sdp_answer", "expires_at"}
        assert body["sdp_answer"]
        assert "call_id" not in body
        assert "openai_call_id" not in body
        assert "client_secret" not in body
        assert "api_key" not in body

    def test_completed_session_blocks_setup(
        self, client, mock_openai_realtime, worker_token_env
    ) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        client.post(
            COMPLETE_PATH,
            headers=auth_headers(exchange.csrf_token, "rtc-complete"),
            cookies=exchange.cookies,
            json={"reason": "participant_ended", "expected_version": version},
        )

        blocked = client.post(
            REALTIME_PATH,
            headers=auth_headers(exchange.csrf_token, "rtc-after-complete"),
            cookies=exchange.cookies,
            json={
                "sdp_offer": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\n",
                "expected_version": version + 1,
            },
        )

        assert blocked.status_code == 409
        assert blocked.json()["error_code"] == "session_already_completed"

    def test_rate_limit_returns_429(
        self, client, mock_openai_realtime, worker_token_env, monkeypatch
    ) -> None:
        from app.services import realtime as realtime_service

        monkeypatch.setattr(realtime_service, "REALTIME_SETUPS_PER_SESSION", 1)

        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        payload = {
            "sdp_offer": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\n",
            "expected_version": version,
        }

        first = client.post(
            REALTIME_PATH,
            headers=auth_headers(exchange.csrf_token, "rtc-rate-1"),
            cookies=exchange.cookies,
            json=payload,
        )
        second = client.post(
            REALTIME_PATH,
            headers=auth_headers(exchange.csrf_token, "rtc-rate-2"),
            cookies=exchange.cookies,
            json=payload,
        )

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["error_code"] == "rate_limited"
