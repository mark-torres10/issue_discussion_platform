from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import FrozenModel, InteractionMode, Speaker, TurnOrigin


class TranscriptTurnView(FrozenModel):
    turn_id: UUID
    speaker: Speaker
    ordinal: int = Field(ge=0)
    display_text: str = Field(max_length=16000)
    source_mode: InteractionMode
    interrupted: bool = False
    recorded_at: datetime


class TranscriptResponse(FrozenModel):
    version: int
    turns: list[TranscriptTurnView]
    cursor: str | None = None


class MessageCreate(FrozenModel):
    client_message_id: UUID
    text: str = Field(min_length=1, max_length=8000)
    client_created_at: datetime | None = None
    expected_version: int = Field(ge=1)


class MessageResponse(FrozenModel):
    operation_id: UUID
    operation_status: "GenerationOperationStatus"
    participant_turn: TranscriptTurnView
    ai_turn: TranscriptTurnView | None = None
    status: "SessionStatus"
    version: int


class TurnRecord(FrozenModel):
    turn_id: UUID
    session_id: UUID
    speaker: Speaker
    ordinal: int = Field(ge=0)
    display_text: str = Field(max_length=16000)
    source_mode: InteractionMode
    origin: TurnOrigin
    interrupted: bool = False
    recorded_at: datetime
    client_message_id: UUID | None = None


from app.models.enums import GenerationOperationStatus, SessionStatus  # noqa: E402

MessageResponse.model_rebuild()
