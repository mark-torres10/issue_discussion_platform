from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.enums import FrozenModel, InteractionMode, SessionStatus, Speaker

EXPORT_MANIFEST_VERSION = "1.0.0"
AI_TEXT_EXPORT_FIELD: Literal["display_text"] = "display_text"


class ExportTurn(FrozenModel):
    turn_id: UUID
    speaker: Speaker
    ordinal: int = Field(ge=0)
    display_text: str = Field(max_length=16000)
    source_mode: InteractionMode
    interrupted: bool = False
    recorded_at: datetime


class SessionExportManifest(FrozenModel):
    manifest_version: str = Field(default=EXPORT_MANIFEST_VERSION, max_length=32)
    ai_text_field: Literal["display_text"] = AI_TEXT_EXPORT_FIELD
    session_id: UUID
    study_id: UUID
    status: SessionStatus
    configuration_snapshot_id: UUID
    telemetry_thread_id: UUID
    consent_version: str | None = None
    consented_at: datetime | None = None
    consent_profile: str | None = None
    consent_withdrawn_at: datetime | None = None
    turns: list[ExportTurn]
