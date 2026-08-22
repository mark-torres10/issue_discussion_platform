import hashlib
import json
from typing import Any

from pydantic import BaseModel

from app.models.transcript import TranscriptResponse, TranscriptTurnView, TurnRecord
from app.services.sessions import CapabilityContext, get_session_view, get_transcript


def project_turn(turn: TurnRecord) -> TranscriptTurnView:
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
    return get_transcript(capability)


def fetch_session_view(capability: CapabilityContext):
    return get_session_view(capability)


def request_hash(model: BaseModel) -> str:
    payload = json.dumps(model.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def request_hash_raw(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
