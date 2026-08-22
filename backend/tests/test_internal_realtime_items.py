from tests.conftest import (
    INTERNAL_REALTIME_ITEMS_PATH,
    REALTIME_PATH,
    auth_headers,
    exchange_invitation,
    start_session,
    worker_auth_headers,
)


def _setup_realtime_call(client, exchange, *, idempotency_key: str = "rtc-ingest-1") -> str:
    started = start_session(client, exchange)
    version = started.json()["session"]["version"]
    response = client.post(
        REALTIME_PATH,
        headers=auth_headers(exchange.csrf_token, idempotency_key),
        cookies=exchange.cookies,
        json={
            "sdp_offer": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\n",
            "expected_version": version,
        },
    )
    assert response.status_code == 200
    from app.services.realtime import get_memory_openai_call_id_for_session
    from app.sample_data.sessions import DEMO_SESSION_ID

    call_id = get_memory_openai_call_id_for_session(DEMO_SESSION_ID)
    assert call_id is not None
    return call_id


class TestInternalIngest:
    def test_maps_provider_item_to_turn(
        self, client, mock_openai_realtime, worker_token_env
    ) -> None:
        exchange = exchange_invitation(client)
        openai_call_id = _setup_realtime_call(client, exchange)
        path = INTERNAL_REALTIME_ITEMS_PATH.format(openai_call_id=openai_call_id)

        response = client.post(
            path,
            headers=worker_auth_headers(),
            json={
                "provider_item_id": "item-abc-123",
                "display_text": "Thanks for sharing that perspective.",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert "turn_id" in body
        assert body["created"] is True

    def test_rejects_participant_cookie(
        self, client, mock_openai_realtime, worker_token_env
    ) -> None:
        exchange = exchange_invitation(client)
        openai_call_id = _setup_realtime_call(client, exchange)
        path = INTERNAL_REALTIME_ITEMS_PATH.format(openai_call_id=openai_call_id)

        response = client.post(
            path,
            headers=auth_headers(exchange.csrf_token),
            cookies=exchange.cookies,
            json={
                "provider_item_id": "item-reject-1",
                "display_text": "Should not be accepted.",
            },
        )

        assert response.status_code in {401, 403}

    def test_duplicate_provider_item_idempotent(
        self, client, mock_openai_realtime, worker_token_env
    ) -> None:
        exchange = exchange_invitation(client)
        openai_call_id = _setup_realtime_call(client, exchange)
        path = INTERNAL_REALTIME_ITEMS_PATH.format(openai_call_id=openai_call_id)
        payload = {
            "provider_item_id": "item-dup-999",
            "display_text": "A canonical provider item.",
        }

        first = client.post(path, headers=worker_auth_headers(), json=payload)
        second = client.post(path, headers=worker_auth_headers(), json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["turn_id"] == second.json()["turn_id"]
        assert first.json()["created"] is True
        assert second.json()["created"] is False

    def test_rejects_missing_worker_token(
        self, client, mock_openai_realtime, worker_token_env
    ) -> None:
        exchange = exchange_invitation(client)
        openai_call_id = _setup_realtime_call(client, exchange)
        path = INTERNAL_REALTIME_ITEMS_PATH.format(openai_call_id=openai_call_id)

        response = client.post(
            path,
            json={
                "provider_item_id": "item-no-token",
                "display_text": "Unauthorized ingest.",
            },
        )

        assert response.status_code in {401, 403}
