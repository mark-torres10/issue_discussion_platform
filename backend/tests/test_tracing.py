from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.integrations.langsmith_envelope import EnvelopeValidationError, validate_metadata
from app.integrations.langsmith_exporter import RecordingLangSmithClient, set_langsmith_client_factory
from app.models.enums import InteractionMode, Speaker, TurnOrigin
from app.models.generation import GenerationOperation, GenerationOperationStatus
from app.models.tracing import TraceExportKind, TraceKind
from app.models.transcript import TurnRecord
from app.repositories.trace_runs import memory_get_trace_run, reset_memory_trace_runs
from app.sample_data.sessions import (
    DEMO_SESSION_ID,
    DEMO_TELEMETRY_THREAD_ID,
    ConfigurationSnapshot,
    build_demo_session_record,
)
from app.services.tracing import DefaultStudyTracingService, SessionDomain, reset_tracing_state
from tests.conftest import (
    COMPLETE_PATH,
    auth_headers,
    exchange_invitation,
    post_message,
    start_session,
    worker_auth_headers,
)


def _session_domain() -> SessionDomain:
    return SessionDomain(
        record=build_demo_session_record(),
        snapshot=ConfigurationSnapshot(),
    )


def _sample_operation() -> GenerationOperation:
    now = datetime.now(UTC)
    return GenerationOperation(
        operation_id=uuid4(),
        session_id=DEMO_SESSION_ID,
        idempotency_scope="messages",
        idempotency_key="trace-op",
        request_hash="hash",
        status=GenerationOperationStatus.succeeded,
        participant_turn_id=uuid4(),
        ai_turn_id=uuid4(),
        model_name="gpt-4.1-mini",
        created_at=now,
        updated_at=now,
    )


class TestNoopExporter:
    def test_flag_off_sends_nothing(
        self, client, mock_openai_client, memory_mode, monkeypatch
    ) -> None:
        recording = RecordingLangSmithClient()
        set_langsmith_client_factory(recording)
        monkeypatch.setenv("TRACE_EXPORT_ENABLED", "false")
        from app.core.config import get_settings

        get_settings.cache_clear()

        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        post_message(
            client,
            exchange,
            text="Universities should protect open debate.",
            expected_version=version,
            idempotency_key="trace-flag-off",
        )

        assert recording.runs == []
        reset_tracing_state()
        get_settings.cache_clear()


class TestEnvelope:
    def test_denies_session_id_in_metadata(self) -> None:
        with pytest.raises(EnvelopeValidationError, match="session_id"):
            validate_metadata(
                {
                    "thread_id": str(DEMO_TELEMETRY_THREAD_ID),
                    "session_id": str(DEMO_SESSION_ID),
                }
            )


class TestGenerationHook:
    def test_commit_succeeds_when_langsmith_down(
        self, client, mock_openai_client, memory_mode, monkeypatch
    ) -> None:
        recording = RecordingLangSmithClient(should_raise=True)
        monkeypatch.setenv("TRACE_EXPORT_ENABLED", "true")
        monkeypatch.setenv("LANGSMITH_API_KEY", "mock")
        monkeypatch.setenv("LANGSMITH_PROJECT", "issue-discussion-local")
        set_langsmith_client_factory(recording)
        from app.core.config import get_settings

        get_settings.cache_clear()

        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        post_message(
            client,
            exchange,
            text="I value open debate on campus.",
            expected_version=version,
            idempotency_key="trace-msg-1",
        )

        complete = client.post(
            COMPLETE_PATH,
            headers=auth_headers(exchange.csrf_token, "trace-complete-down"),
            cookies=exchange.cookies,
            json={"reason": "participant_ended", "expected_version": version + 1},
        )

        assert complete.status_code == 200
        reset_tracing_state()
        get_settings.cache_clear()


class TestRunIdPersistence:
    def test_retry_reuses_root_run_id(self, monkeypatch) -> None:
        recording = RecordingLangSmithClient()
        monkeypatch.setenv("TRACE_EXPORT_ENABLED", "true")
        monkeypatch.setenv("LANGSMITH_API_KEY", "mock")
        monkeypatch.setenv("LANGSMITH_PROJECT", "issue-discussion-local")
        set_langsmith_client_factory(recording)
        from app.core.config import get_settings

        get_settings.cache_clear()
        reset_memory_trace_runs()

        domain = _session_domain()
        participant_id = uuid4()
        ai_id = uuid4()
        now = datetime.now(UTC)
        participant_turn = TurnRecord(
            turn_id=participant_id,
            session_id=DEMO_SESSION_ID,
            speaker=Speaker.participant,
            ordinal=1,
            display_text="Participant view",
            source_mode=InteractionMode.text,
            origin=TurnOrigin.study_api_text,
            recorded_at=now,
        )
        ai_turn = TurnRecord(
            turn_id=ai_id,
            session_id=DEMO_SESSION_ID,
            speaker=Speaker.ai,
            ordinal=2,
            display_text="AI reply",
            source_mode=InteractionMode.text,
            origin=TurnOrigin.study_api_text,
            recorded_at=now,
        )
        operation = _sample_operation().model_copy(
            update={"participant_turn_id": participant_id, "ai_turn_id": ai_id}
        )
        service = DefaultStudyTracingService()
        service.on_generation_committed(domain, participant_turn, ai_turn, operation)
        service.on_generation_committed(domain, participant_turn, ai_turn, operation)

        conversation_runs = [
            run for run in recording.runs if run["name"] == "conversation_turn"
        ]
        assert len(conversation_runs) == 2
        assert conversation_runs[0]["run_id"] == conversation_runs[1]["run_id"]
        stored = memory_get_trace_run(ai_id, export_kind=TraceExportKind.conversation_turn)
        assert stored is not None
        assert stored.langsmith_root_run_id == conversation_runs[0]["run_id"]
        reset_tracing_state()
        get_settings.cache_clear()


class TestOpeningTurn:
    def test_start_hook_does_not_create_conversation_turn_for_opening(
        self, client, memory_mode, monkeypatch
    ) -> None:
        recording = RecordingLangSmithClient()
        monkeypatch.setenv("TRACE_EXPORT_ENABLED", "true")
        monkeypatch.setenv("LANGSMITH_API_KEY", "mock")
        monkeypatch.setenv("LANGSMITH_PROJECT", "issue-discussion-local")
        set_langsmith_client_factory(recording)
        from app.core.config import get_settings

        get_settings.cache_clear()

        exchange = exchange_invitation(client)
        start_session(client, exchange)

        conversation_runs = [
            run for run in recording.runs if run.get("name") == "conversation_turn"
        ]
        assert conversation_runs == []
        reset_tracing_state()
        get_settings.cache_clear()


class TestVoiceIngestHook:
    def test_ingest_commit_triggers_voice_trace_kind(
        self, client, mock_openai_realtime, worker_token_env, monkeypatch
    ) -> None:
        recording = RecordingLangSmithClient()
        monkeypatch.setenv("TRACE_EXPORT_ENABLED", "true")
        monkeypatch.setenv("LANGSMITH_API_KEY", "mock")
        monkeypatch.setenv("LANGSMITH_PROJECT", "issue-discussion-local")
        set_langsmith_client_factory(recording)
        from app.core.config import get_settings

        get_settings.cache_clear()

        exchange = exchange_invitation(client)
        started = start_session(client, exchange)
        version = started.json()["session"]["version"]
        rtc = client.post(
            "/v1/participant-session/realtime/calls",
            headers=auth_headers(exchange.csrf_token, "trace-voice-rtc"),
            cookies=exchange.cookies,
            json={
                "sdp_offer": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\n",
                "expected_version": version,
            },
        )
        assert rtc.status_code == 200
        from app.services.realtime import get_memory_openai_call_id_for_session

        openai_call_id = get_memory_openai_call_id_for_session(DEMO_SESSION_ID)
        assert openai_call_id is not None

        ingest = client.post(
            f"/internal/v1/realtime/calls/{openai_call_id}/items",
            headers=worker_auth_headers(),
            json={
                "provider_item_id": "trace-voice-item-1",
                "display_text": "Voice response from provider.",
            },
        )
        assert ingest.status_code == 200

        conversation_runs = [
            run for run in recording.runs if run.get("name") == "conversation_turn"
        ]
        assert len(conversation_runs) == 1
        metadata = conversation_runs[0]["extra"]["metadata"]
        assert metadata["trace_kind"] == TraceKind.provider_observed_realtime_response.value
        assert metadata["thread_id"] == str(DEMO_TELEMETRY_THREAD_ID)
        assert "session_id" not in metadata
        reset_tracing_state()
        get_settings.cache_clear()
