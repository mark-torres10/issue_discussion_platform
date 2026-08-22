from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import ConnectionState, FrozenModel, ObservationType


class ObservationCreate(FrozenModel):
    observation_id: UUID
    observation_type: ObservationType
    occurred_at: datetime
    connection_state: ConnectionState | None = None
    client_first_audio_observed_ms: int | None = Field(default=None, ge=0)
    client_first_transcript_observed_ms: int | None = Field(default=None, ge=0)


class ObservationAck(FrozenModel):
    accepted: bool = True
    observation_id: UUID
    untrusted: bool = True


class ObservationBatchCreate(FrozenModel):
    observations: list[ObservationCreate] = Field(min_length=1, max_length=20)
    expected_version: int = Field(ge=1)


class ObservationBatchResponse(FrozenModel):
    accepted: list[ObservationAck]
    version: int
