from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.enums import FrozenModel, GenerationOperationStatus


class GenerationOperation(FrozenModel):
    operation_id: UUID
    session_id: UUID
    idempotency_scope: str = Field(max_length=128)
    idempotency_key: str = Field(max_length=256)
    request_hash: str = Field(max_length=128)
    status: GenerationOperationStatus
    participant_turn_id: UUID | None = None
    ai_turn_id: UUID | None = None
    model_name: str = Field(max_length=128)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=512)
    response_body: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
