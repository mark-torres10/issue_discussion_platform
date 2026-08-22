from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import FrozenModel


class RealtimeCallCreateRequest(FrozenModel):
    sdp_offer: str = Field(min_length=1, max_length=100_000)
    expected_version: int = Field(ge=1)


class RealtimeCallCreateResponse(FrozenModel):
    sdp_answer: str
    expires_at: datetime


class RealtimeProviderItemIngest(FrozenModel):
    provider_item_id: str = Field(min_length=1, max_length=256)
    display_text: str = Field(min_length=1, max_length=16000)
    provider_response_id: str | None = Field(default=None, max_length=256)
    interrupted: bool = False
    provider_created_at: datetime | None = None


class RealtimeProviderItemIngestResponse(FrozenModel):
    turn_id: UUID
    created: bool

