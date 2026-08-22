from datetime import datetime

from pydantic import Field

from app.models.enums import FrozenModel


class RealtimeCallCreateRequest(FrozenModel):
    sdp_offer: str = Field(min_length=1, max_length=100_000)
    expected_version: int = Field(ge=1)


class RealtimeCallCreateResponse(FrozenModel):
    sdp_answer: str
    expires_at: datetime
