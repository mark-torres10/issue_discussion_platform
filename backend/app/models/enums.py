from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionStatus(StrEnum):
    pending = "pending"
    active = "active"
    paused = "paused"
    completed = "completed"
    expired = "expired"


class InteractionMode(StrEnum):
    voice = "voice"
    text = "text"


class Speaker(StrEnum):
    participant = "participant"
    ai = "ai"
    system = "system"


class TurnOrigin(StrEnum):
    study_api_text = "study_api_text"
    snapshot_opening = "snapshot_opening"
    provider_realtime = "provider_realtime"
    client_observation = "client_observation"
    revision = "revision"


class ConnectionState(StrEnum):
    idle = "idle"
    listening = "listening"
    thinking = "thinking"
    speaking = "speaking"
    muted = "muted"
    reconnecting = "reconnecting"
    disconnected = "disconnected"
    finished = "finished"


class ObservationType(StrEnum):
    session_opened = "session_opened"
    microphone_permission = "microphone_permission"
    muted = "muted"
    unmuted = "unmuted"
    interrupted_ai = "interrupted_ai"
    connection_lost = "connection_lost"
    connection_restored = "connection_restored"
    first_audio_heard = "first_audio_heard"
    first_transcript_seen = "first_transcript_seen"
    client_reported_problem = "client_reported_problem"


class GenerationOperationStatus(StrEnum):
    accepted = "accepted"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
