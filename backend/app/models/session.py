from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, HttpUrl

from app.models.enums import FrozenModel, InteractionMode, SessionStatus


class IssueConfig(FrozenModel):
    issue_id: str = Field(max_length=64)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=2000)


class AiPersonaPublic(FrozenModel):
    display_name: str = Field(max_length=80)
    label: str = Field(default="AI participant", max_length=80)
    short_introduction: str = Field(max_length=500)
    avatar_url: HttpUrl
    avatar_version: str = Field(max_length=64)
    voice_name: str | None = Field(default=None, max_length=64)
    voice_version: str | None = Field(default=None, max_length=64)
    assigned_position: str = Field(max_length=200)


class SessionRulesPublic(FrozenModel):
    target_duration_seconds: int = Field(ge=60, le=3600)
    warn_remaining_seconds: int = Field(default=60, ge=0)
    allow_interrupt: bool = True
    allow_text_fallback: bool = True
    ai_speaks_first: bool = True
    show_exact_remaining_time: bool = False
    allow_resume: bool = True


class ParticipantSessionView(FrozenModel):
    status: SessionStatus
    version: int = Field(ge=1)
    writer_role: Literal["writer", "read_only"]
    study_wave: str = Field(max_length=64)
    issue: IssueConfig
    ai_persona: AiPersonaPublic
    prompt_version: str = Field(max_length=64)
    rules: SessionRulesPublic
    preferred_mode: InteractionMode = InteractionMode.voice
    started_at: datetime | None = None
    ends_at: datetime | None = None
    completed_at: datetime | None = None
    next_instruction: str | None = Field(default=None, max_length=500)


class SessionRecord(FrozenModel):
    session_id: UUID
    study_id: UUID
    participant_capability_hash: str
    telemetry_thread_id: UUID
    status: SessionStatus
    version: int
    writer_lease_id: UUID | None = None
    writer_lease_expires_at: datetime | None = None
    configuration_snapshot_id: UUID
    consent_version: str | None = None
    consented_at: datetime | None = None
    consent_profile: str | None = None
    consent_withdrawn_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion_reason: str | None = None


class AccessExchangeRequest(FrozenModel):
    invitation_token: str = Field(min_length=32, max_length=256)


class SessionStartRequest(FrozenModel):
    preferred_mode: InteractionMode = InteractionMode.voice
    expected_version: int = Field(ge=1)
    client_started_at: datetime | None = None


class SessionStartResponse(FrozenModel):
    session: ParticipantSessionView
    opening_turn: "TranscriptTurnView | None" = None


class SessionCompleteRequest(FrozenModel):
    reason: str = Field(default="participant_ended", max_length=64)
    expected_version: int = Field(ge=1)
    client_completed_at: datetime | None = None
    recovery_observations: list["ObservationCreate"] = Field(
        default_factory=list, max_length=20
    )


class SessionCompleteResponse(FrozenModel):
    session: ParticipantSessionView
    saved_turn_count: int


class ConsentRecordRequest(FrozenModel):
    consent_version: str = Field(min_length=1, max_length=64)
    consent_profile: str = Field(min_length=1, max_length=64)
    allowed_modes: list[InteractionMode] = Field(min_length=1, max_length=2)
    withdrawn: bool = False
    expected_version: int = Field(ge=1)


class SessionPauseRequest(FrozenModel):
    expected_version: int = Field(ge=1)


class WriterLeaseTransferRequest(FrozenModel):
    transfer_nonce: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=1)


from app.models.observations import ObservationCreate  # noqa: E402
from app.models.transcript import TranscriptTurnView  # noqa: E402

SessionStartResponse.model_rebuild()
SessionCompleteRequest.model_rebuild()
