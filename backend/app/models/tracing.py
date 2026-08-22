from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.enums import FrozenModel, InteractionMode


class TraceKind(StrEnum):
    instrumented_text_generation = "instrumented_text_generation"
    provider_observed_realtime_response = "provider_observed_realtime_response"
    client_reconstructed_voice_turn = "client_reconstructed_voice_turn"


class TraceExportKind(StrEnum):
    conversation_turn = "conversation_turn"
    session_lifecycle = "session_lifecycle"
    connection_failure = "connection_failure"


class SessionEvent(FrozenModel):
    event_type: str = Field(max_length=64)
    error_code: str | None = Field(default=None, max_length=64)
    occurred_at: datetime | None = None


class TraceEnvelope(FrozenModel):
    trace_schema_version: str = Field(max_length=16)
    trace_policy_version: str = Field(max_length=64)
    trace_kind: TraceKind
    langsmith_run_id: UUID
    telemetry_thread_id: UUID
    canonical_turn_id: UUID | None = None
    provider_response_id: str | None = Field(default=None, max_length=256)
    ls_agent_type: str = Field(default="chain", max_length=32)
    ls_message_format: str = Field(default="langsmith", max_length=32)
    study_wave: str = Field(max_length=64)
    protocol_version: str = Field(max_length=64)
    configuration_snapshot_id: UUID
    issue_version: str = Field(max_length=64)
    prompt_version: str = Field(max_length=64)
    avatar_version: str | None = Field(default=None, max_length=64)
    voice_version: str | None = Field(default=None, max_length=64)
    interaction_mode: InteractionMode
    model_provider: str = Field(max_length=64)
    model_name: str = Field(max_length=128)
    frontend_build_revision: str | None = Field(default=None, max_length=64)
    backend_build_revision: str | None = Field(default=None, max_length=64)
    metric_source: str = Field(max_length=64)
    approved_inputs: dict[str, Any] = Field(default_factory=dict)
    approved_outputs: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] | None = None
    timing: dict[str, Any] | None = None


class TraceRunRecord(FrozenModel):
    trace_run_id: UUID
    session_id: UUID
    export_kind: TraceExportKind
    langsmith_root_run_id: UUID
    canonical_turn_id: UUID | None = None
    trace_kind: TraceKind | None = None
    created_at: datetime
