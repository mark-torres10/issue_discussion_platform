from uuid import uuid4

import pytest

from app.integrations import openai_client
from app.models.enums import GenerationOperationStatus
from tests.conftest import MOCK_AI_TEXT, exchange_invitation, post_message, start_session


class TestMessages:
    def test_scripted_ai_reply(self, client, mock_openai_client) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        response = post_message(
            client,
            exchange,
            text="I think universities should set clear limits.",
            expected_version=version,
            idempotency_key="msg-1",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["participant_turn"]["display_text"].startswith("I think")
        assert body["ai_turn"] is not None
        assert body["ai_turn"]["display_text"] == MOCK_AI_TEXT

    def test_duplicate_idempotency_key_returns_stored_response(
        self, client, mock_openai_client
    ) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        message_id = str(uuid4())

        first = post_message(
            client,
            exchange,
            text="Same payload",
            expected_version=version,
            idempotency_key="msg-idem",
            client_message_id=message_id,
        )
        second = post_message(
            client,
            exchange,
            text="Same payload",
            expected_version=version,
            idempotency_key="msg-idem",
            client_message_id=message_id,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()

    def test_idempotency_conflict_on_same_key_different_hash(
        self, client, mock_openai_client
    ) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        first = post_message(
            client,
            exchange,
            text="First text",
            expected_version=version,
            idempotency_key="msg-conflict",
        )
        assert first.status_code == 200

        conflict = post_message(
            client,
            exchange,
            text="Different text",
            expected_version=version,
            idempotency_key="msg-conflict",
        )

        assert conflict.status_code == 409
        assert conflict.json()["error_code"] == "idempotency_conflict"

    def test_forged_ai_turn_field_rejected(self, client) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        response = client.post(
            "/v1/participant-session/messages",
            headers={
                "X-CSRF-Token": exchange.csrf_token,
                "Idempotency-Key": "msg-forged",
            },
            cookies=exchange.cookies,
            json={
                "client_message_id": str(uuid4()),
                "text": "hello",
                "expected_version": version,
                "ai_turn": {"display_text": "forged"},
            },
        )

        assert response.status_code == 400
        assert response.json()["error_code"] == "validation_error"


class TestMessagesEndpoint:
    def test_creates_ai_turn_server_side(self, client, mock_openai_client) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        response = post_message(
            client,
            exchange,
            text="I think universities should set clear limits.",
            expected_version=version,
            idempotency_key="msg-server-ai",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["participant_turn"]["display_text"].startswith("I think")
        assert body["ai_turn"] is not None
        assert body["ai_turn"]["display_text"] == MOCK_AI_TEXT
        assert body["operation_status"] == GenerationOperationStatus.succeeded.value
        assert mock_openai_client.chat.completions.call_count == 1

    def test_openai_failure_returns_503(
        self, client, monkeypatch: pytest.MonkeyPatch, memory_mode
    ) -> None:
        from unittest.mock import MagicMock

        monkeypatch.setenv("OPENAI_API_KEY", "mock")
        monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini")

        failing_client = MagicMock()
        failing_client.chat.completions.create.side_effect = RuntimeError("provider down")
        openai_client.set_openai_client_factory(lambda: failing_client)

        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        response = post_message(
            client,
            exchange,
            text="I think universities should set clear limits.",
            expected_version=version,
            idempotency_key="msg-fail-1",
        )

        assert response.status_code == 503
        assert response.json()["error_code"] == "generation_failed"
        assert response.json()["retryable"] is True
        openai_client.set_openai_client_factory(None)
