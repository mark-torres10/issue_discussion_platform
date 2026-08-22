from tests.conftest import REALTIME_PATH, auth_headers, exchange_invitation, start_session


class TestRealtimeSample:
    def test_returns_sdp_answer_only(self, client) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        response = client.post(
            REALTIME_PATH,
            headers=auth_headers(exchange.csrf_token, "rtc-1"),
            cookies=exchange.cookies,
            json={
                "sdp_offer": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\n",
                "expected_version": version,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert "sdp_answer" in body
        assert body["sdp_answer"]
        assert "expires_at" in body
        assert "call_id" not in body
        assert "api_key" not in body
        assert "client_secret" not in body
