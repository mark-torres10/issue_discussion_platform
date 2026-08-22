from tests.conftest import START_PATH, auth_headers, exchange_invitation, start_session


class TestSessionStart:
    def test_start_idempotency_returns_same_response(self, client) -> None:
        exchange = exchange_invitation(client)
        headers = auth_headers(exchange.csrf_token, "start-idem-1")
        payload = {"preferred_mode": "text", "expected_version": 1}

        first = client.post(
            START_PATH,
            headers=headers,
            cookies=exchange.cookies,
            json=payload,
        )
        second = client.post(
            START_PATH,
            headers=headers,
            cookies=exchange.cookies,
            json=payload,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()

    def test_version_conflict_returns_409(self, client) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        assert started.status_code == 200
        version = started.json()["session"]["version"]

        conflict = client.post(
            START_PATH,
            headers=auth_headers(exchange.csrf_token, "start-conflict"),
            cookies=exchange.cookies,
            json={"preferred_mode": "text", "expected_version": version - 1},
        )

        assert conflict.status_code == 409
        assert conflict.json()["error_code"] == "version_conflict"

    def test_opening_turn_when_ai_speaks_first(self, client) -> None:
        exchange = exchange_invitation(client)
        response = start_session(client, exchange)

        assert response.status_code == 200
        body = response.json()
        assert body["opening_turn"] is not None
        assert body["opening_turn"]["speaker"] == "ai"
        assert body["session"]["status"] == "active"
