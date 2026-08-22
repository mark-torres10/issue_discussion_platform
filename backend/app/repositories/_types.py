"""Shared row shapes and identifier helpers for Postgres repositories."""

import hashlib
import os
import time
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import FrozenModel


def new_uuid7() -> UUID:
    """Return a time-ordered UUID v7 for repository primary keys."""
    timestamp_ms = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF
    uuid_int = (timestamp_ms & 0xFFFFFFFFFFFF) << 80
    uuid_int |= 0x7000 << 64
    uuid_int |= rand_a << 64
    uuid_int |= 0x8000000000000000
    uuid_int |= rand_b
    return UUID(int=uuid_int)


def hash_invitation_token(token: str) -> str:
    """Return the SHA-256 hex digest of an invitation token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ConfigurationSnapshotRecord(FrozenModel):
    """Immutable study configuration captured at session start."""
    configuration_snapshot_id: UUID
    study_id: UUID
    study_wave: str = Field(max_length=64)
    protocol_version: str = Field(max_length=64)
    issue_version: str = Field(max_length=64)
    persona_version: str = Field(max_length=64)
    prompt_content_hash: str = Field(max_length=128)
    prompt_object_reference: str = Field(max_length=512)
    opening_display_text: str = Field(max_length=16000)
    ai_speaks_first: bool = True
    model_provider: str = Field(max_length=64)
    model_name: str = Field(max_length=128)
    model_parameters_json: dict[str, object] = Field(default_factory=dict)
    voice_config_json: dict[str, object] = Field(default_factory=dict)
    tool_manifest_hash: str = Field(max_length=128)
    safety_policy_version: str = Field(max_length=64)
    assignment_seed_reference: str = Field(max_length=256)
    application_version: str = Field(max_length=64)
    created_at: datetime | None = None


class InvitationRecord(FrozenModel):
    """Immutable invitation row linking a token hash to a pending session."""
    invitation_id: UUID
    study_id: UUID
    session_id: UUID
    token_hash: str
    telemetry_thread_id: UUID
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None


class AuditEventRecord(FrozenModel):
    """Immutable staff or system action recorded for compliance review."""
    audit_event_id: UUID
    study_id: UUID
    actor_type: str = Field(max_length=64)
    actor_id: str | None = Field(default=None, max_length=128)
    action: str = Field(max_length=128)
    object_type: str = Field(max_length=64)
    object_id: str = Field(max_length=128)
    authorization_result: str = Field(max_length=32)
    request_id: str | None = Field(default=None, max_length=128)
    object_version: int | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime | None = None
