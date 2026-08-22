"""Participant transcript projections and request hashing helpers."""

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.models.transcript import TranscriptResponse, TranscriptTurnView, TurnRecord
from app.services.sessions import CapabilityContext, get_session_view, get_transcript


def project_turn(turn: TurnRecord) -> TranscriptTurnView:
    """Map a stored turn record to the participant-visible view shape."""
    return TranscriptTurnView(
        turn_id=turn.turn_id,
        speaker=turn.speaker,
        ordinal=turn.ordinal,
        display_text=turn.display_text,
        source_mode=turn.source_mode,
        interrupted=turn.interrupted,
        recorded_at=turn.recorded_at,
    )


def fetch_transcript(capability: CapabilityContext) -> TranscriptResponse:
    """Return the committed transcript for the capability's session."""
    return get_transcript(capability)


def fetch_session_view(capability: CapabilityContext):
    """Return the participant session view for the capability."""
    return get_session_view(capability)


def request_hash(model: BaseModel) -> str:
    """Return a stable SHA-256 hash of a Pydantic model's JSON payload."""
    payload = json.dumps(model.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def request_hash_raw(payload: dict[str, Any]) -> str:
    """Return a stable SHA-256 hash of a JSON-serializable mapping."""
    body = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
