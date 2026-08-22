from app.sample_data.invitations import UNKNOWN_INVITATION_TOKEN
from tests.conftest import EXCHANGE_PATH, SESSION_PATH, exchange_invitation


class TestParticipantAccess:
    def test_unknown_token_returns_not_found(self, client) -> None:
        response = client.post(
            EXCHANGE_PATH,
            json={"invitation_token": UNKNOWN_INVITATION_TOKEN},
        )

        assert response.status_code == 404
        body = response.json()
        assert body["error_code"] in {"session_not_found", "session_unavailable"}

    def test_first_exchange_is_writer(self, client) -> None:
        exchange = exchange_invitation(client)

        assert exchange.response.status_code == 200
        body = exchange.response.json()
        assert body["writer_role"] == "writer"
        assert "session_id" not in body
        assert exchange.csrf_token

    def test_second_exchange_is_read_only(self, client) -> None:
        first = exchange_invitation(client)
        assert first.response.status_code == 200

        second = exchange_invitation(client)
        assert second.response.status_code == 200
        assert second.response.json()["writer_role"] == "read_only"

    def test_protected_route_requires_cookie(self, client) -> None:
        response = client.get(SESSION_PATH)

        assert response.status_code == 401
        assert response.json()["error_code"] == "capability_missing"

    def test_csrf_required_on_state_changing_post(self, client) -> None:
        exchange = exchange_invitation(client)
        response = client.post(
            "/v1/participant-session/start",
            cookies=exchange.cookies,
            headers={},
            json={"preferred_mode": "text", "expected_version": 1},
        )

        assert response.status_code == 403
        assert response.json()["error_code"] == "csrf_rejected"
