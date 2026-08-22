"""Allowlisted LangSmith trace envelope builder."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.models.enums import InteractionMode
from app.models.generation import GenerationOperation
from app.models.session import SessionRecord
from app.models.tracing import TraceEnvelope, TraceKind
from app.models.transcript import TurnRecord
from app.sample_data.sessions import ConfigurationSnapshot

TRACE_SCHEMA_VERSION = "1"
TRACE_POLICY_VERSION = "noop-v1"

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "session_id",
        "invitation_token",
        "invitation_hash",
        "participant_email",
        "email",
        "capability_id",
        "capability_cookie",
        "csrf_token",
        "participant_capability_hash",
        "openai_call_id",
        "client_secret",
        "sdp_offer",
        "sdp_answer",
    }
)

ALLOWED_METADATA_KEYS = frozenset(
    {
        "thread_id",
        "session_id_compat",
        "trace_schema_version",
        "trace_policy_version",
        "trace_kind",
        "study_wave",
        "protocol_version",
        "configuration_snapshot_id",
        "issue_version",
        "prompt_version",
        "avatar_version",
        "voice_version",
        "interaction_mode",
        "model_provider",
        "ls_provider",
        "ls_model_name",
        "ls_agent_type",
        "ls_message_format",
        "canonical_turn_id",
        "provider_response_id",
        "metric_source",
        "backend_build_revision",
        "lifecycle_event",
    }
)


class EnvelopeValidationError(ValueError):
    """Raised when envelope or metadata contains disallowed fields."""


def validate_metadata(metadata: dict[str, Any]) -> None:
    """Reject metadata keys outside the LangSmith export allowlist.

    Raises
    ------
    EnvelopeValidationError
        If a forbidden or unknown key is present, or compat ids disagree.
    """
    for key in metadata:
        if key in FORBIDDEN_METADATA_KEYS:
            raise EnvelopeValidationError(
                f"Forbidden metadata key for LangSmith export: {key}"
            )
        if key not in ALLOWED_METADATA_KEYS:
            raise EnvelopeValidationError(
                f"Metadata key not on allowlist for LangSmith export: {key}"
            )
    thread_id = metadata.get("thread_id")
    if thread_id is not None and metadata.get("session_id_compat") is not None:
        if str(metadata["session_id_compat"]) != str(thread_id):
            raise EnvelopeValidationError(
                "session_id_compat must match thread_id when both are present"
            )


def envelope_to_metadata(envelope: TraceEnvelope) -> dict[str, str]:
    """Build allowlisted LangSmith metadata from a trace envelope."""
    metadata = {
        "thread_id": str(envelope.telemetry_thread_id),
        "session_id_compat": str(envelope.telemetry_thread_id),
        "trace_schema_version": envelope.trace_schema_version,
        "trace_policy_version": envelope.trace_policy_version,
        "trace_kind": envelope.trace_kind.value,
        "study_wave": envelope.study_wave,
        "protocol_version": envelope.protocol_version,
        "configuration_snapshot_id": str(envelope.configuration_snapshot_id),
        "issue_version": envelope.issue_version,
        "prompt_version": envelope.prompt_version,
        "interaction_mode": envelope.interaction_mode.value,
        "model_provider": envelope.model_provider,
        "ls_provider": envelope.model_provider,
        "ls_model_name": envelope.model_name,
        "ls_agent_type": envelope.ls_agent_type,
        "ls_message_format": envelope.ls_message_format,
        "metric_source": envelope.metric_source,
    }
    if envelope.avatar_version is not None:
        metadata["avatar_version"] = envelope.avatar_version
    if envelope.voice_version is not None:
        metadata["voice_version"] = envelope.voice_version
    if envelope.canonical_turn_id is not None:
        metadata["canonical_turn_id"] = str(envelope.canonical_turn_id)
    if envelope.provider_response_id is not None:
        metadata["provider_response_id"] = envelope.provider_response_id
    if envelope.backend_build_revision is not None:
        metadata["backend_build_revision"] = envelope.backend_build_revision
    validate_metadata(metadata)
    return metadata


def _snapshot_metadata(
    record: SessionRecord,
    snapshot: ConfigurationSnapshot,
) -> dict[str, str | UUID]:
    settings = get_settings()
    return {
        "study_wave": snapshot.study_wave,
        "protocol_version": snapshot.prompt_version,
        "configuration_snapshot_id": record.configuration_snapshot_id,
        "issue_version": snapshot.issue.issue_id,
        "prompt_version": snapshot.prompt_version,
        "avatar_version": snapshot.ai_persona.avatar_version,
        "voice_version": snapshot.ai_persona.voice_version,
        "model_provider": getattr(snapshot, "model_provider", "openai"),
        "model_name": getattr(snapshot, "model_name", "gpt-4.1-mini"),
        "backend_build_revision": settings.railway_git_commit_sha,
    }


def build_text_generation_envelope(
    *,
    record: SessionRecord,
    snapshot: ConfigurationSnapshot,
    participant_turn: TurnRecord | None,
    ai_turn: TurnRecord,
    operation: GenerationOperation,
    langsmith_run_id: UUID,
) -> TraceEnvelope:
    """Build a LangSmith envelope for an instrumented text generation turn."""
    inputs_messages: list[dict[str, str]] = []
    if participant_turn is not None:
        inputs_messages.append(
            {"role": "user", "content": participant_turn.display_text}
        )
    outputs_messages = [{"role": "assistant", "content": ai_turn.display_text}]
    meta = _snapshot_metadata(record, snapshot)
    return TraceEnvelope(
        trace_schema_version=TRACE_SCHEMA_VERSION,
        trace_policy_version=TRACE_POLICY_VERSION,
        trace_kind=TraceKind.instrumented_text_generation,
        langsmith_run_id=langsmith_run_id,
        telemetry_thread_id=record.telemetry_thread_id,
        canonical_turn_id=ai_turn.turn_id,
        ls_agent_type="chain",
        ls_message_format="langsmith",
        study_wave=str(meta["study_wave"]),
        protocol_version=str(meta["protocol_version"]),
        configuration_snapshot_id=record.configuration_snapshot_id,
        issue_version=str(meta["issue_version"]),
        prompt_version=str(meta["prompt_version"]),
        avatar_version=str(meta["avatar_version"]) if meta["avatar_version"] else None,
        voice_version=str(meta["voice_version"]) if meta.get("voice_version") else None,
        interaction_mode=ai_turn.source_mode,
        model_provider=str(meta["model_provider"]),
        model_name=operation.model_name,
        backend_build_revision=(
            str(meta["backend_build_revision"])
            if meta["backend_build_revision"]
            else None
        ),
        metric_source="server",
        approved_inputs={"messages": inputs_messages},
        approved_outputs={"messages": outputs_messages},
    )


def build_voice_turn_envelope(
    *,
    record: SessionRecord,
    snapshot: ConfigurationSnapshot,
    ai_turn: TurnRecord,
    trace_kind: TraceKind,
    langsmith_run_id: UUID,
    provider_response_id: str | None = None,
) -> TraceEnvelope:
    """Build a LangSmith envelope for a provider-observed voice turn."""
    meta = _snapshot_metadata(record, snapshot)
    return TraceEnvelope(
        trace_schema_version=TRACE_SCHEMA_VERSION,
        trace_policy_version=TRACE_POLICY_VERSION,
        trace_kind=trace_kind,
        langsmith_run_id=langsmith_run_id,
        telemetry_thread_id=record.telemetry_thread_id,
        canonical_turn_id=ai_turn.turn_id,
        provider_response_id=provider_response_id,
        ls_agent_type="chain",
        ls_message_format="langsmith",
        study_wave=str(meta["study_wave"]),
        protocol_version=str(meta["protocol_version"]),
        configuration_snapshot_id=record.configuration_snapshot_id,
        issue_version=str(meta["issue_version"]),
        prompt_version=str(meta["prompt_version"]),
        avatar_version=str(meta["avatar_version"]) if meta["avatar_version"] else None,
        voice_version=str(meta["voice_version"]) if meta.get("voice_version") else None,
        interaction_mode=InteractionMode.voice,
        model_provider=str(meta["model_provider"]),
        model_name=str(meta["model_name"]),
        backend_build_revision=(
            str(meta["backend_build_revision"])
            if meta["backend_build_revision"]
            else None
        ),
        metric_source="provider_sideband",
        approved_inputs={"messages": []},
        approved_outputs={
            "messages": [{"role": "assistant", "content": ai_turn.display_text}]
        },
    )


def build_lifecycle_envelope(
    *,
    record: SessionRecord,
    snapshot: ConfigurationSnapshot,
    langsmith_run_id: UUID,
    lifecycle_event: str,
    interaction_mode: InteractionMode = InteractionMode.voice,
) -> TraceEnvelope:
    """Build a LangSmith envelope for a session lifecycle event."""
    meta = _snapshot_metadata(record, snapshot)
    return TraceEnvelope(
        trace_schema_version=TRACE_SCHEMA_VERSION,
        trace_policy_version=TRACE_POLICY_VERSION,
        trace_kind=TraceKind.instrumented_text_generation,
        langsmith_run_id=langsmith_run_id,
        telemetry_thread_id=record.telemetry_thread_id,
        ls_agent_type="chain",
        ls_message_format="langsmith",
        study_wave=str(meta["study_wave"]),
        protocol_version=str(meta["protocol_version"]),
        configuration_snapshot_id=record.configuration_snapshot_id,
        issue_version=str(meta["issue_version"]),
        prompt_version=str(meta["prompt_version"]),
        avatar_version=str(meta["avatar_version"]) if meta["avatar_version"] else None,
        voice_version=str(meta["voice_version"]) if meta.get("voice_version") else None,
        interaction_mode=interaction_mode,
        model_provider=str(meta["model_provider"]),
        model_name=str(meta["model_name"]),
        backend_build_revision=(
            str(meta["backend_build_revision"])
            if meta["backend_build_revision"]
            else None
        ),
        metric_source="server",
        approved_inputs={"lifecycle_event": lifecycle_event},
        approved_outputs={},
    )


def build_connection_failure_envelope(
    *,
    record: SessionRecord,
    snapshot: ConfigurationSnapshot,
    langsmith_run_id: UUID,
    event_type: str,
    error_code: str | None,
) -> TraceEnvelope:
    """Build a LangSmith envelope for a realtime connection failure."""
    meta = _snapshot_metadata(record, snapshot)
    return TraceEnvelope(
        trace_schema_version=TRACE_SCHEMA_VERSION,
        trace_policy_version=TRACE_POLICY_VERSION,
        trace_kind=TraceKind.provider_observed_realtime_response,
        langsmith_run_id=langsmith_run_id,
        telemetry_thread_id=record.telemetry_thread_id,
        ls_agent_type="chain",
        ls_message_format="langsmith",
        study_wave=str(meta["study_wave"]),
        protocol_version=str(meta["protocol_version"]),
        configuration_snapshot_id=record.configuration_snapshot_id,
        issue_version=str(meta["issue_version"]),
        prompt_version=str(meta["prompt_version"]),
        avatar_version=str(meta["avatar_version"]) if meta["avatar_version"] else None,
        voice_version=str(meta["voice_version"]) if meta.get("voice_version") else None,
        interaction_mode=InteractionMode.voice,
        model_provider=str(meta["model_provider"]),
        model_name=str(meta["model_name"]),
        backend_build_revision=(
            str(meta["backend_build_revision"])
            if meta["backend_build_revision"]
            else None
        ),
        metric_source="server",
        approved_inputs={"event_type": event_type, "error_code": error_code or ""},
        approved_outputs={},
    )
