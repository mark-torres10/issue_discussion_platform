from uuid import uuid4

import pytest

from app.models.enums import GenerationOperationStatus
from app.models.transcript import MessageCreate
from app.sample_data.sessions import DEMO_SESSION_ID
from app.services.generation import _memory_get_operation, create_message
from app.services.sessions import CapabilityContext
from tests.conftest import exchange_invitation, post_message, start_session


def _writer_capability(csrf_token: str = "csrf") -> CapabilityContext:
    return CapabilityContext(
        session_id=DEMO_SESSION_ID,
        capability_id="writer-test",
        writer_role="writer",
        csrf_token=csrf_token,
    )


class TestGenerationOperation:
    def test_idempotent_retry_skips_model(
        self, client, mock_openai_client, memory_mode
    ) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        message_id = str(uuid4())

        first = post_message(
            client,
            exchange,
            text="I think universities should set clear limits.",
            expected_version=version,
            idempotency_key="gen-idem-1",
            client_message_id=message_id,
        )
        second = post_message(
            client,
            exchange,
            text="I think universities should set clear limits.",
            expected_version=version,
            idempotency_key="gen-idem-1",
            client_message_id=message_id,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()
        assert mock_openai_client.chat.completions.call_count == 1

    def test_operation_state_transitions(
        self, client, mock_openai_client, memory_mode
    ) -> None:
        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]

        create_message(
            _writer_capability(exchange.csrf_token),
            MessageCreate(
                client_message_id=uuid4(),
                text="My view is that open debate matters.",
                expected_version=version,
            ),
            idempotency_key="op-state-1",
            request_hash="hash-1",
        )

        operation = _memory_get_operation(
            DEMO_SESSION_ID, "messages", "op-state-1"
        )
        assert operation is not None
        assert operation.status == GenerationOperationStatus.succeeded
        assert operation.participant_turn_id is not None
        assert operation.ai_turn_id is not None
