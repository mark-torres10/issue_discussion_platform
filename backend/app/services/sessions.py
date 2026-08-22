import asyncio
import hashlib
import secrets
import threading
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypeVar
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.csrf import generate_csrf_token

from app.models.enums import (
    GenerationOperationStatus,
    InteractionMode,
    SessionStatus,
    Speaker,
    TurnOrigin,
)
from app.models.observations import (
    ObservationAck,
    ObservationBatchCreate,
    ObservationBatchResponse,
    ObservationCreate,
)
from app.models.realtime import RealtimeCallCreateRequest, RealtimeCallCreateResponse
from app.models.session import (
    AccessExchangeRequest,
    ConsentRecordRequest,
    ParticipantSessionView,
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionPauseRequest,
    SessionRecord,
    SessionStartRequest,
    SessionStartResponse,
    WriterLeaseTransferRequest,
)
from app.models.transcript import (
    MessageCreate,
    MessageResponse,
    TranscriptResponse,
    TranscriptTurnView,
    TurnRecord,
)
from app.sample_data.invitations import hash_invitation_token
from app.sample_data.sessions import (
    DEMO_COMPLETION_NEXT_STEP,
    DEMO_ISSUE,
    DEMO_OPENING_MESSAGE,
    DEMO_PROMPT_VERSION,
    DEMO_RULES,
    DEMO_STUDY_WAVE,
    ConfigurationSnapshot,
    INVITATION_TOKEN_HASHES,
    build_demo_session_record,
)

T = TypeVar("T")

GRACE_PERIOD = timedelta(hours=24)
WRITER_LEASE_DURATION = timedelta(minutes=30)
FAKE_SDP_ANSWER = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=sample-contracts\r\n"


def _postgres_enabled() -> bool:
    return get_settings().use_postgres


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


class StudyApiError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        retryable: bool = False,
        current_version: int | None = None,
        session_status: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.retryable = retryable
        self.current_version = current_version
        self.session_status = session_status


def utc_now() -> datetime:
    return datetime.now(UTC)


def _new_uuid7() -> UUID:
    import os
    import time

    timestamp_ms = int(time.time() * 1000)
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF
    uuid_int = (timestamp_ms & 0xFFFFFFFFFFFF) << 80
    uuid_int |= 0x7000 << 64
    uuid_int |= rand_a << 64
    uuid_int |= 0x8000000000000000
    uuid_int |= rand_b
    return UUID(int=uuid_int)


class CapabilityContext:
    def __init__(
        self,
        *,
        session_id: UUID,
        capability_id: str,
        writer_role: Literal["writer", "read_only"],
        csrf_token: str,
    ) -> None:
        self.session_id = session_id
        self.capability_id = capability_id
        self.writer_role = writer_role
        self.csrf_token = csrf_token


class IdempotencyRecord:
    def __init__(self, request_hash: str, response_body: dict[str, Any]) -> None:
        self.request_hash = request_hash
        self.response_body = response_body


class SessionState:
    def __init__(self) -> None:
        self.record: SessionRecord
        self.snapshot: ConfigurationSnapshot
        self.turns: list[TurnRecord] = []
        self.observations: list[ObservationCreate] = []
        self.writer_exchanged: bool = False
        self.transfer_nonces: dict[str, str] = {}
        self.idempotency: dict[tuple[str, str], IdempotencyRecord] = {}
        self.message_count: int = 0
        self.realtime_setup_count: int = 0


class MemorySessionStore:
    def __init__(self) -> None:
        self.sessions: dict[UUID, SessionState] = {}
        self._seed()

    def reset(self) -> None:
        self.sessions.clear()
        self._seed()

    def _seed(self) -> None:
        record = build_demo_session_record()
        state = SessionState()
        state.record = record
        state.snapshot = ConfigurationSnapshot()
        self.sessions[record.session_id] = state


_store = MemorySessionStore()
_complete_lock = threading.Lock()


def get_store() -> MemorySessionStore:
    return _store


def reset_store() -> None:
    _store.reset()


def _get_state(session_id: UUID) -> SessionState:
    state = _store.sessions.get(session_id)
    if state is None:
        raise StudyApiError(
            status_code=404,
            error_code="session_not_found",
            message="Session not found",
        )
    return state


def _ensure_writable(state: SessionState, capability: CapabilityContext) -> None:
    record = state.record
    if record.status == SessionStatus.completed:
        if record.completed_at and utc_now() <= record.completed_at + GRACE_PERIOD:
            raise StudyApiError(
                status_code=409,
                error_code="session_already_completed",
                message="Session is already completed",
                session_status=record.status.value,
                current_version=record.version,
            )
        raise StudyApiError(
            status_code=410,
            error_code="session_unavailable",
            message="Session is no longer available",
        )
    if record.status == SessionStatus.expired:
        raise StudyApiError(
            status_code=410,
            error_code="session_unavailable",
            message="Session has expired",
        )
    if capability.writer_role != "writer":
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="Writer lease required",
            current_version=record.version,
        )
    if record.writer_lease_id is None:
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="No active writer lease",
            current_version=record.version,
        )
    if (
        record.writer_lease_expires_at is not None
        and utc_now() > record.writer_lease_expires_at
    ):
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="Writer lease expired",
            current_version=record.version,
        )


def _check_version(state: SessionState, expected_version: int) -> None:
    if state.record.version != expected_version:
        raise StudyApiError(
            status_code=409,
            error_code="version_conflict",
            message="Session version conflict",
            retryable=True,
            current_version=state.record.version,
            session_status=state.record.status.value,
        )


def _check_consent(state: SessionState) -> None:
    if not state.snapshot.consent_required:
        return
    record = state.record
    if record.consent_withdrawn_at is not None:
        raise StudyApiError(
            status_code=403,
            error_code="consent_required",
            message="Consent has been withdrawn",
        )
    if record.consented_at is None:
        raise StudyApiError(
            status_code=403,
            error_code="consent_required",
            message="Consent is required before this action",
        )


def _idempotency_scope(route: str) -> str:
    return route


def _get_idempotency(
    state: SessionState, scope: str, key: str
) -> IdempotencyRecord | None:
    return state.idempotency.get((scope, key))


def _store_idempotency(
    state: SessionState, scope: str, key: str, request_hash: str, body: dict[str, Any]
) -> None:
    state.idempotency[(scope, key)] = IdempotencyRecord(request_hash, body)


def _check_idempotency(
    state: SessionState,
    *,
    scope: str,
    key: str,
    request_hash: str,
) -> dict[str, Any] | None:
    existing = _get_idempotency(state, scope, key)
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise StudyApiError(
            status_code=409,
            error_code="idempotency_conflict",
            message="Idempotency key reused with different request body",
            current_version=state.record.version,
        )
    return existing.response_body


def _issue_writer_lease(state: SessionState) -> None:
    now = utc_now()
    state.record = state.record.model_copy(
        update={
            "writer_lease_id": _new_uuid7(),
            "writer_lease_expires_at": now + WRITER_LEASE_DURATION,
        }
    )


def _renew_writer_lease(state: SessionState) -> None:
    now = utc_now()
    state.record = state.record.model_copy(
        update={"writer_lease_expires_at": now + WRITER_LEASE_DURATION}
    )


def _project_session(
    state: SessionState, writer_role: Literal["writer", "read_only"]
) -> ParticipantSessionView:
    record = state.record
    snapshot = state.snapshot
    next_instruction = None
    if record.status == SessionStatus.completed:
        next_instruction = snapshot.completion_next_step
    ends_at = None
    if record.started_at is not None:
        ends_at = record.started_at + timedelta(
            seconds=snapshot.rules.target_duration_seconds
        )
    return ParticipantSessionView(
        status=record.status,
        version=record.version,
        writer_role=writer_role,
        study_wave=snapshot.study_wave,
        issue=snapshot.issue,
        ai_persona=snapshot.ai_persona,
        prompt_version=snapshot.prompt_version,
        rules=snapshot.rules,
        preferred_mode=InteractionMode.voice,
        started_at=record.started_at,
        ends_at=ends_at,
        completed_at=record.completed_at,
        next_instruction=next_instruction,
    )


def _turn_to_view(turn: TurnRecord) -> TranscriptTurnView:
    return TranscriptTurnView(
        turn_id=turn.turn_id,
        speaker=turn.speaker,
        ordinal=turn.ordinal,
        display_text=turn.display_text,
        source_mode=turn.source_mode,
        interrupted=turn.interrupted,
        recorded_at=turn.recorded_at,
    )


def exchange_access(
    body: AccessExchangeRequest,
) -> tuple[ParticipantSessionView, CapabilityContext, bool]:
    if _postgres_enabled():
        return _run_async(_pg_exchange_access(body))
    token_hash = hash_invitation_token(body.invitation_token)
    session_id = INVITATION_TOKEN_HASHES.get(token_hash)
    if session_id is None:
        raise StudyApiError(
            status_code=404,
            error_code="session_not_found",
            message="Invitation token is not valid",
        )
    state = _get_state(session_id)
    record = state.record
    if record.status == SessionStatus.expired:
        raise StudyApiError(
            status_code=404,
            error_code="session_unavailable",
            message="Session is unavailable",
        )
    if (
        record.status == SessionStatus.completed
        and record.completed_at is not None
        and utc_now() > record.completed_at + GRACE_PERIOD
    ):
        raise StudyApiError(
            status_code=410,
            error_code="session_unavailable",
            message="Session grace period has ended",
        )

    if not state.writer_exchanged:
        writer_role: Literal["writer", "read_only"] = "writer"
        state.writer_exchanged = True
        _issue_writer_lease(state)
    else:
        writer_role = "read_only"
        nonce = secrets.token_urlsafe(24)
        state.transfer_nonces[nonce] = "pending"

    capability_id = f"{writer_role}-{_new_uuid7()}"
    csrf_token = generate_csrf_token()
    capability = CapabilityContext(
        session_id=session_id,
        capability_id=capability_id,
        writer_role=writer_role,
        csrf_token=csrf_token,
    )
    view = _project_session(state, writer_role)
    return view, capability, True


def get_session_view(capability: CapabilityContext) -> ParticipantSessionView:
    if _postgres_enabled():
        return _run_async(_pg_get_session_view(capability))
    state = _get_state(capability.session_id)
    return _project_session(state, capability.writer_role)


def record_consent(
    capability: CapabilityContext,
    body: ConsentRecordRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
    if _postgres_enabled():
        return _run_async(_pg_record_consent(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("consent")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ParticipantSessionView.model_validate(cached)

    _ensure_writable(state, capability)
    _check_version(state, body.expected_version)
    now = utc_now()
    if body.withdrawn:
        state.record = state.record.model_copy(
            update={
                "consent_withdrawn_at": now,
                "version": state.record.version + 1,
                "writer_lease_id": None,
                "writer_lease_expires_at": None,
            }
        )
    else:
        state.record = state.record.model_copy(
            update={
                "consent_version": body.consent_version,
                "consent_profile": body.consent_profile,
                "consented_at": now,
                "consent_withdrawn_at": None,
                "version": state.record.version + 1,
            }
        )
    view = _project_session(state, capability.writer_role)
    _store_idempotency(state, scope, idempotency_key, request_hash, view.model_dump())
    return view


def start_session(
    capability: CapabilityContext,
    body: SessionStartRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> SessionStartResponse:
    if _postgres_enabled():
        return _run_async(_pg_start_session(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("start")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return SessionStartResponse.model_validate(cached)

    _ensure_writable(state, capability)
    _check_version(state, body.expected_version)
    _check_consent(state)
    record = state.record
    if record.status not in (SessionStatus.pending, SessionStatus.paused):
        if record.status == SessionStatus.active:
            response = SessionStartResponse(
                session=_project_session(state, capability.writer_role),
                opening_turn=None,
            )
            _store_idempotency(
                state, scope, idempotency_key, request_hash, response.model_dump()
            )
            return response
        raise StudyApiError(
            status_code=409,
            error_code="session_not_started",
            message="Session cannot be started from current status",
            session_status=record.status.value,
            current_version=record.version,
        )

    now = utc_now()
    opening_turn: TranscriptTurnView | None = None
    if state.snapshot.rules.ai_speaks_first and not state.turns:
        turn = TurnRecord(
            turn_id=_new_uuid7(),
            session_id=record.session_id,
            speaker=Speaker.ai,
            ordinal=0,
            display_text=state.snapshot.opening_message,
            source_mode=body.preferred_mode,
            origin=TurnOrigin.snapshot_opening,
            recorded_at=now,
        )
        state.turns.append(turn)
        opening_turn = _turn_to_view(turn)

    state.record = record.model_copy(
        update={
            "status": SessionStatus.active,
            "started_at": record.started_at or now,
            "version": record.version + 1,
        }
    )
    _issue_writer_lease(state)
    response = SessionStartResponse(
        session=_project_session(state, capability.writer_role),
        opening_turn=opening_turn,
    )
    _store_idempotency(
        state, scope, idempotency_key, request_hash, response.model_dump()
    )
    from app.services.tracing import SessionDomain, get_tracing_service

    opening_record = None
    if opening_turn is not None:
        for turn in state.turns:
            if turn.turn_id == opening_turn.turn_id:
                opening_record = turn
                break
    get_tracing_service().on_session_started(
        SessionDomain(record=state.record, snapshot=state.snapshot),
        preferred_mode=body.preferred_mode,
        opening_turn=opening_record,
    )
    return response


def create_message(
    capability: CapabilityContext,
    body: MessageCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> MessageResponse:
    if _postgres_enabled():
        return _run_async(_pg_create_message(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("messages")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return MessageResponse.model_validate(cached)

    _ensure_writable(state, capability)
    _check_version(state, body.expected_version)
    _check_consent(state)
    if state.record.status != SessionStatus.active:
        raise StudyApiError(
            status_code=409,
            error_code="session_not_started",
            message="Session must be active to send messages",
            session_status=state.record.status.value,
            current_version=state.record.version,
        )

    for turn in state.turns:
        if turn.client_message_id == body.client_message_id:
            raise StudyApiError(
                status_code=409,
                error_code="turn_conflict",
                message="Client message id already used",
                current_version=state.record.version,
            )

    now = utc_now()
    participant_turn = TurnRecord(
        turn_id=_new_uuid7(),
        session_id=state.record.session_id,
        speaker=Speaker.participant,
        ordinal=len(state.turns),
        display_text=body.text,
        source_mode=InteractionMode.text,
        origin=TurnOrigin.study_api_text,
        recorded_at=body.client_created_at or now,
        client_message_id=body.client_message_id,
    )
    state.turns.append(participant_turn)

    replies = state.snapshot.scripted_ai_replies
    ai_text = replies[state.message_count % len(replies)]
    state.message_count += 1
    ai_turn = TurnRecord(
        turn_id=_new_uuid7(),
        session_id=state.record.session_id,
        speaker=Speaker.ai,
        ordinal=len(state.turns),
        display_text=ai_text,
        source_mode=InteractionMode.text,
        origin=TurnOrigin.study_api_text,
        recorded_at=utc_now(),
    )
    state.turns.append(ai_turn)

    state.record = state.record.model_copy(update={"version": state.record.version + 1})
    _renew_writer_lease(state)

    operation_id = _new_uuid7()
    response = MessageResponse(
        operation_id=operation_id,
        operation_status=GenerationOperationStatus.succeeded,
        participant_turn=_turn_to_view(participant_turn),
        ai_turn=_turn_to_view(ai_turn),
        status=state.record.status,
        version=state.record.version,
    )
    _store_idempotency(
        state, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response


def record_observations(
    capability: CapabilityContext,
    body: ObservationBatchCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ObservationBatchResponse:
    if _postgres_enabled():
        return _run_async(_pg_record_observations(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("observations")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ObservationBatchResponse.model_validate(cached)

    _ensure_writable(state, capability)
    _check_version(state, body.expected_version)

    acks: list[ObservationAck] = []
    for observation in body.observations:
        state.observations.append(observation)
        acks.append(
            ObservationAck(
                accepted=True,
                observation_id=observation.observation_id,
                untrusted=True,
            )
        )

    state.record = state.record.model_copy(update={"version": state.record.version + 1})
    _renew_writer_lease(state)
    response = ObservationBatchResponse(accepted=acks, version=state.record.version)
    _store_idempotency(
        state, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response


def get_transcript(capability: CapabilityContext) -> TranscriptResponse:
    if _postgres_enabled():
        return _run_async(_pg_get_transcript(capability))
    state = _get_state(capability.session_id)
    turns = [_turn_to_view(turn) for turn in state.turns]
    return TranscriptResponse(version=state.record.version, turns=turns)


def complete_session(
    capability: CapabilityContext,
    body: SessionCompleteRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> SessionCompleteResponse:
    if _postgres_enabled():
        return _run_async(_pg_complete_session(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("complete")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return SessionCompleteResponse.model_validate(cached)

    with _complete_lock:
        state = _get_state(capability.session_id)
        cached = _check_idempotency(
            state, scope=scope, key=idempotency_key, request_hash=request_hash
        )
        if cached is not None:
            return SessionCompleteResponse.model_validate(cached)

        _ensure_writable(state, capability)
        _check_version(state, body.expected_version)

        if state.record.status == SessionStatus.completed:
            response = SessionCompleteResponse(
                session=_project_session(state, capability.writer_role),
                saved_turn_count=len(state.turns),
            )
            return response

        for observation in body.recovery_observations:
            state.observations.append(observation)

        now = utc_now()
        state.record = state.record.model_copy(
            update={
                "status": SessionStatus.completed,
                "completed_at": now,
                "completion_reason": body.reason,
                "version": state.record.version + 1,
                "writer_lease_id": None,
                "writer_lease_expires_at": None,
            }
        )
        response = SessionCompleteResponse(
            session=_project_session(state, capability.writer_role),
            saved_turn_count=len(state.turns),
        )
        _store_idempotency(
            state, scope, idempotency_key, request_hash, response.model_dump()
        )
        from app.services.tracing import SessionDomain, get_tracing_service

        get_tracing_service().on_session_completed(
            SessionDomain(record=state.record, snapshot=state.snapshot)
        )
        return response


def pause_session(
    capability: CapabilityContext,
    body: SessionPauseRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
    if _postgres_enabled():
        return _run_async(_pg_pause_session(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("pause")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ParticipantSessionView.model_validate(cached)

    _ensure_writable(state, capability)
    _check_version(state, body.expected_version)
    if not state.snapshot.rules.allow_resume:
        raise StudyApiError(
            status_code=409,
            error_code="session_not_started",
            message="Pause is not allowed for this session",
        )
    if state.record.status != SessionStatus.active:
        raise StudyApiError(
            status_code=409,
            error_code="session_not_started",
            message="Only active sessions can be paused",
            session_status=state.record.status.value,
        )
    state.record = state.record.model_copy(
        update={
            "status": SessionStatus.paused,
            "version": state.record.version + 1,
        }
    )
    view = _project_session(state, capability.writer_role)
    _store_idempotency(state, scope, idempotency_key, request_hash, view.model_dump())
    return view


def transfer_writer_lease(
    capability: CapabilityContext,
    body: WriterLeaseTransferRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
    if _postgres_enabled():
        return _run_async(_pg_transfer_writer_lease(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("transfer")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ParticipantSessionView.model_validate(cached)

    _ensure_writable(state, capability)
    _check_version(state, body.expected_version)
    if body.transfer_nonce not in state.transfer_nonces:
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="Invalid transfer nonce",
        )
    _issue_writer_lease(state)
    state.record = state.record.model_copy(update={"version": state.record.version + 1})
    view = _project_session(state, "writer")
    _store_idempotency(state, scope, idempotency_key, request_hash, view.model_dump())
    return view


def create_realtime_call(
    capability: CapabilityContext,
    body: RealtimeCallCreateRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> RealtimeCallCreateResponse:
    if _postgres_enabled():
        return _run_async(_pg_create_realtime_call(capability, body, idempotency_key=idempotency_key, request_hash=request_hash))
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("realtime")
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return RealtimeCallCreateResponse.model_validate(cached)

    _ensure_writable(state, capability)
    _check_version(state, body.expected_version)
    _check_consent(state)
    if state.record.status != SessionStatus.active:
        raise StudyApiError(
            status_code=409,
            error_code="session_not_started",
            message="Session must be active for realtime setup",
        )

    state.realtime_setup_count += 1
    _renew_writer_lease(state)
    response = RealtimeCallCreateResponse(
        sdp_answer=FAKE_SDP_ANSWER,
        expires_at=utc_now() + timedelta(minutes=5),
    )
    _store_idempotency(
        state, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response

# ---------------------------------------------------------------------------
# Postgres durable storage backend
# ---------------------------------------------------------------------------

_pg_idempotency: dict[tuple[UUID, str, str], IdempotencyRecord] = {}
_pg_transfer_nonces: dict[UUID, dict[str, str]] = {}


def reset_postgres_ephemeral_state() -> None:
    _pg_idempotency.clear()
    _pg_transfer_nonces.clear()


def _pg_idempotency_scope(route: str) -> str:
    return route


def _pg_get_idempotency(
    session_id: UUID, scope: str, key: str
) -> IdempotencyRecord | None:
    return _pg_idempotency.get((session_id, scope, key))


def _pg_store_idempotency(
    session_id: UUID,
    scope: str,
    key: str,
    request_hash: str,
    body: dict[str, Any],
) -> None:
    _pg_idempotency[(session_id, scope, key)] = IdempotencyRecord(request_hash, body)


def _pg_check_idempotency(
    session_id: UUID,
    *,
    scope: str,
    key: str,
    request_hash: str,
) -> dict[str, Any] | None:
    existing = _pg_get_idempotency(session_id, scope, key)
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise StudyApiError(
            status_code=409,
            error_code="idempotency_conflict",
            message="Idempotency key reused with different request body",
        )
    return existing.response_body


def _turn_content_hash(display_text: str) -> str:
    return hashlib.sha256(display_text.encode("utf-8")).hexdigest()


def _snapshot_config_from_record(snapshot: "ConfigurationSnapshotRecord") -> ConfigurationSnapshot:
    config = ConfigurationSnapshot()
    config.study_wave = snapshot.study_wave
    config.prompt_version = snapshot.protocol_version
    config.opening_message = snapshot.opening_display_text
    config.rules = DEMO_RULES.model_copy(
        update={"ai_speaks_first": snapshot.ai_speaks_first}
    )
    return config


def _project_session_from_parts(
    record: SessionRecord,
    snapshot: ConfigurationSnapshot,
    writer_role: Literal["writer", "read_only"],
) -> ParticipantSessionView:
    next_instruction = None
    if record.status == SessionStatus.completed:
        next_instruction = snapshot.completion_next_step
    ends_at = None
    if record.started_at is not None:
        ends_at = record.started_at + timedelta(
            seconds=snapshot.rules.target_duration_seconds
        )
    return ParticipantSessionView(
        status=record.status,
        version=record.version,
        writer_role=writer_role,
        study_wave=snapshot.study_wave,
        issue=snapshot.issue,
        ai_persona=snapshot.ai_persona,
        prompt_version=snapshot.prompt_version,
        rules=snapshot.rules,
        preferred_mode=InteractionMode.voice,
        started_at=record.started_at,
        ends_at=ends_at,
        completed_at=record.completed_at,
        next_instruction=next_instruction,
    )


def _pg_ensure_writable(record: SessionRecord, capability: CapabilityContext) -> None:
    if record.status == SessionStatus.completed:
        if record.completed_at and utc_now() <= record.completed_at + GRACE_PERIOD:
            raise StudyApiError(
                status_code=409,
                error_code="session_already_completed",
                message="Session is already completed",
                session_status=record.status.value,
                current_version=record.version,
            )
        raise StudyApiError(
            status_code=410,
            error_code="session_unavailable",
            message="Session is no longer available",
        )
    if record.status == SessionStatus.expired:
        raise StudyApiError(
            status_code=410,
            error_code="session_unavailable",
            message="Session has expired",
        )
    if capability.writer_role != "writer":
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="Writer lease required",
            current_version=record.version,
        )
    if record.writer_lease_id is None:
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="No active writer lease",
            current_version=record.version,
        )
    if (
        record.writer_lease_expires_at is not None
        and utc_now() > record.writer_lease_expires_at
    ):
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="Writer lease expired",
            current_version=record.version,
        )


def _pg_check_version(record: SessionRecord, expected_version: int) -> None:
    if record.version != expected_version:
        raise StudyApiError(
            status_code=409,
            error_code="version_conflict",
            message="Session version conflict",
            retryable=True,
            current_version=record.version,
            session_status=record.status.value,
        )


def _pg_check_consent(record: SessionRecord, snapshot: ConfigurationSnapshot) -> None:
    if not snapshot.consent_required:
        return
    if record.consent_withdrawn_at is not None:
        raise StudyApiError(
            status_code=403,
            error_code="consent_required",
            message="Consent has been withdrawn",
        )
    if record.consented_at is None:
        raise StudyApiError(
            status_code=403,
            error_code="consent_required",
            message="Consent is required before this action",
        )


async def _pg_load_session_bundle(
    db: AsyncSession, session_id: UUID
) -> tuple[SessionRecord, ConfigurationSnapshot]:
    from app.repositories.sessions import SessionRepository
    from app.repositories.snapshots import SnapshotRepository

    session_repo = SessionRepository(db)
    record = await session_repo.get(session_id)
    snapshot_repo = SnapshotRepository(db)
    snapshot_row = await snapshot_repo.get(record.configuration_snapshot_id)
    return record, _snapshot_config_from_record(snapshot_row)


async def _pg_count_turns(db: AsyncSession, session_id: UUID) -> int:
    result = await db.execute(
        text("SELECT COUNT(*) FROM canonical_turns WHERE session_id = :session_id"),
        {"session_id": session_id},
    )
    return int(result.scalar_one())


async def _pg_list_turns(db: AsyncSession, session_id: UUID) -> list[TurnRecord]:
    result = await db.execute(
        text(
            """
            SELECT turn_id, session_id, speaker, ordinal, display_text,
                   source_mode, origin, interrupted, recorded_at
            FROM canonical_turns
            WHERE session_id = :session_id
            ORDER BY ordinal ASC
            """
        ),
        {"session_id": session_id},
    )
    turns: list[TurnRecord] = []
    for row in result.mappings():
        turns.append(
            TurnRecord(
                turn_id=row["turn_id"],
                session_id=row["session_id"],
                speaker=Speaker(row["speaker"]),
                ordinal=row["ordinal"],
                display_text=row["display_text"],
                source_mode=InteractionMode(row["source_mode"]),
                origin=TurnOrigin(row["origin"]),
                interrupted=row["interrupted"],
                recorded_at=row["recorded_at"],
            )
        )
    return turns


def _pg_session():
    from app.db.session import get_db_session

    return get_db_session()


async def _pg_version_conflict(db: AsyncSession, session_id: UUID) -> None:
    record, _ = await _pg_load_session_bundle(db, session_id)
    raise StudyApiError(
        status_code=409,
        error_code="version_conflict",
        message="Session version conflict",
        retryable=True,
        current_version=record.version,
        session_status=record.status.value,
    )


async def _pg_exchange_access(
    body: AccessExchangeRequest,
) -> tuple[ParticipantSessionView, CapabilityContext, bool]:
    from app.repositories.invitations import InvitationRepository

    token_hash = hash_invitation_token(body.invitation_token)
    async with _pg_session() as db:
        invitation_repo = InvitationRepository(db)
        invitation = await invitation_repo.get_by_token_hash(token_hash)
        if invitation is None:
            raise StudyApiError(
                status_code=404,
                error_code="session_not_found",
                message="Invitation token is not valid",
            )
        record, snapshot = await _pg_load_session_bundle(db, invitation.session_id)

    if record.status == SessionStatus.expired:
        raise StudyApiError(
            status_code=404,
            error_code="session_unavailable",
            message="Session is unavailable",
        )
    if (
        record.status == SessionStatus.completed
        and record.completed_at is not None
        and utc_now() > record.completed_at + GRACE_PERIOD
    ):
        raise StudyApiError(
            status_code=410,
            error_code="session_unavailable",
            message="Session grace period has ended",
        )

    if not record.participant_capability_hash:
        writer_role: Literal["writer", "read_only"] = "writer"
        async with _pg_session() as db:
            now = utc_now()
            lease_id = _new_uuid7()
            await db.execute(
                text(
                    """
                    UPDATE sessions
                    SET participant_capability_hash = :hash,
                        writer_lease_id = :lease_id,
                        writer_lease_expires_at = :expires_at,
                        updated_at = now()
                    WHERE session_id = :session_id
                    """
                ),
                {
                    "hash": token_hash[:64],
                    "lease_id": lease_id,
                    "expires_at": now + WRITER_LEASE_DURATION,
                    "session_id": record.session_id,
                },
            )
            await db.commit()
            record = record.model_copy(
                update={
                    "participant_capability_hash": token_hash[:64],
                    "writer_lease_id": lease_id,
                    "writer_lease_expires_at": now + WRITER_LEASE_DURATION,
                }
            )
    else:
        writer_role = "read_only"
        nonce = secrets.token_urlsafe(24)
        _pg_transfer_nonces.setdefault(record.session_id, {})[nonce] = "pending"

    capability = CapabilityContext(
        session_id=record.session_id,
        capability_id=f"{writer_role}-{_new_uuid7()}",
        writer_role=writer_role,
        csrf_token=generate_csrf_token(),
    )
    view = _project_session_from_parts(record, snapshot, writer_role)
    return view, capability, True


async def _pg_get_session_view(capability: CapabilityContext) -> ParticipantSessionView:
    async with _pg_session() as db:
        record, snapshot = await _pg_load_session_bundle(db, capability.session_id)
    return _project_session_from_parts(record, snapshot, capability.writer_role)


async def _pg_record_consent(
    capability: CapabilityContext,
    body: ConsentRecordRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
    scope = _pg_idempotency_scope("consent")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ParticipantSessionView.model_validate(cached)

    async with _pg_session() as db:
        record, snapshot = await _pg_load_session_bundle(db, capability.session_id)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)
        now = utc_now()
        if body.withdrawn:
            sql = """
                UPDATE sessions
                SET consent_withdrawn_at = :withdrawn_at,
                    version = version + 1,
                    writer_lease_id = NULL,
                    writer_lease_expires_at = NULL,
                    updated_at = now()
                WHERE session_id = :session_id AND version = :expected_version
                RETURNING *
            """
            params = {
                "withdrawn_at": now,
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            }
        else:
            sql = """
                UPDATE sessions
                SET consent_version = :consent_version,
                    consent_profile = :consent_profile,
                    consented_at = :consented_at,
                    consent_withdrawn_at = NULL,
                    version = version + 1,
                    updated_at = now()
                WHERE session_id = :session_id AND version = :expected_version
                RETURNING *
            """
            params = {
                "consent_version": body.consent_version,
                "consent_profile": body.consent_profile,
                "consented_at": now,
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            }
        result = await db.execute(text(sql), params)
        row = result.mappings().first()
        if row is None:
            await _pg_version_conflict(db, capability.session_id)
        await db.commit()
        from app.repositories.sessions import SessionRepository

        record = SessionRepository._row_to_record(row)

    view = _project_session_from_parts(record, snapshot, capability.writer_role)
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, view.model_dump()
    )
    return view


async def _pg_start_session(
    capability: CapabilityContext,
    body: SessionStartRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> SessionStartResponse:
    scope = _pg_idempotency_scope("start")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return SessionStartResponse.model_validate(cached)

    async with _pg_session() as db:
        record, snapshot = await _pg_load_session_bundle(db, capability.session_id)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)
        _pg_check_consent(record, snapshot)

        if record.status not in (SessionStatus.pending, SessionStatus.paused):
            if record.status == SessionStatus.active:
                response = SessionStartResponse(
                    session=_project_session_from_parts(
                        record, snapshot, capability.writer_role
                    ),
                    opening_turn=None,
                )
                _pg_store_idempotency(
                    capability.session_id,
                    scope,
                    idempotency_key,
                    request_hash,
                    response.model_dump(),
                )
                return response
            raise StudyApiError(
                status_code=409,
                error_code="session_not_started",
                message="Session cannot be started from current status",
                session_status=record.status.value,
                current_version=record.version,
            )

        now = utc_now()
        opening_turn: TranscriptTurnView | None = None
        turn_count = await _pg_count_turns(db, capability.session_id)
        if snapshot.rules.ai_speaks_first and turn_count == 0:
            turn_id = _new_uuid7()
            display_text = snapshot.opening_message
            await db.execute(
                text(
                    """
                    INSERT INTO canonical_turns (
                        turn_id, session_id, ordinal, speaker, origin,
                        verification_status, source_mode, display_text,
                        interrupted, content_hash, recorded_at, schema_version
                    ) VALUES (
                        :turn_id, :session_id, 0, :speaker, :origin,
                        'verified', :source_mode, :display_text,
                        false, :content_hash, :recorded_at, 1
                    )
                    """
                ),
                {
                    "turn_id": turn_id,
                    "session_id": capability.session_id,
                    "speaker": Speaker.ai.value,
                    "origin": TurnOrigin.snapshot_opening.value,
                    "source_mode": body.preferred_mode.value,
                    "display_text": display_text,
                    "content_hash": _turn_content_hash(display_text),
                    "recorded_at": now,
                },
            )
            opening_turn = TranscriptTurnView(
                turn_id=turn_id,
                speaker=Speaker.ai,
                ordinal=0,
                display_text=display_text,
                source_mode=body.preferred_mode,
                interrupted=False,
                recorded_at=now,
            )

        lease_id = _new_uuid7()
        result = await db.execute(
            text(
                """
                UPDATE sessions
                SET status = 'active',
                    started_at = COALESCE(started_at, :started_at),
                    version = version + 1,
                    writer_lease_id = :lease_id,
                    writer_lease_expires_at = :expires_at,
                    updated_at = now()
                WHERE session_id = :session_id AND version = :expected_version
                RETURNING *
                """
            ),
            {
                "started_at": now,
                "lease_id": lease_id,
                "expires_at": now + WRITER_LEASE_DURATION,
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            },
        )
        row = result.mappings().first()
        if row is None:
            await _pg_version_conflict(db, capability.session_id)
        await db.commit()
        from app.repositories.sessions import SessionRepository

        record = SessionRepository._row_to_record(row)

    response = SessionStartResponse(
        session=_project_session_from_parts(record, snapshot, capability.writer_role),
        opening_turn=opening_turn,
    )
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, response.model_dump()
    )
    from app.services.tracing import SessionDomain, get_tracing_service

    opening_record = None
    if opening_turn is not None:
        opening_record = TurnRecord(
            turn_id=opening_turn.turn_id,
            session_id=capability.session_id,
            speaker=opening_turn.speaker,
            ordinal=opening_turn.ordinal,
            display_text=opening_turn.display_text,
            source_mode=opening_turn.source_mode,
            origin=TurnOrigin.snapshot_opening,
            recorded_at=opening_turn.recorded_at,
        )
    get_tracing_service().on_session_started(
        SessionDomain(record=record, snapshot=snapshot),
        preferred_mode=body.preferred_mode,
        opening_turn=opening_record,
    )
    return response


async def _pg_create_message(
    capability: CapabilityContext,
    body: MessageCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> MessageResponse:
    scope = _pg_idempotency_scope("messages")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return MessageResponse.model_validate(cached)

    async with _pg_session() as db:
        record, snapshot = await _pg_load_session_bundle(db, capability.session_id)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)
        _pg_check_consent(record, snapshot)
        if record.status != SessionStatus.active:
            raise StudyApiError(
                status_code=409,
                error_code="session_not_started",
                message="Session must be active to send messages",
                session_status=record.status.value,
                current_version=record.version,
            )

        dup = await db.execute(
            text(
                """
                SELECT 1 FROM canonical_turns
                WHERE session_id = :session_id AND client_event_id = :client_message_id
                """
            ),
            {
                "session_id": capability.session_id,
                "client_message_id": body.client_message_id,
            },
        )
        if dup.first() is not None:
            raise StudyApiError(
                status_code=409,
                error_code="turn_conflict",
                message="Client message id already used",
                current_version=record.version,
            )

        now = utc_now()
        ordinal = await _pg_count_turns(db, capability.session_id)
        participant_turn_id = _new_uuid7()
        participant_text = body.text
        await db.execute(
            text(
                """
                INSERT INTO canonical_turns (
                    turn_id, session_id, ordinal, speaker, origin,
                    verification_status, client_event_id, source_mode,
                    display_text, interrupted, content_hash, recorded_at, schema_version
                ) VALUES (
                    :turn_id, :session_id, :ordinal, :speaker, :origin,
                    'verified', :client_event_id, :source_mode,
                    :display_text, false, :content_hash, :recorded_at, 1
                )
                """
            ),
            {
                "turn_id": participant_turn_id,
                "session_id": capability.session_id,
                "ordinal": ordinal,
                "speaker": Speaker.participant.value,
                "origin": TurnOrigin.study_api_text.value,
                "client_event_id": body.client_message_id,
                "source_mode": InteractionMode.text.value,
                "display_text": participant_text,
                "content_hash": _turn_content_hash(participant_text),
                "recorded_at": body.client_created_at or now,
            },
        )
        participant_turn = TurnRecord(
            turn_id=participant_turn_id,
            session_id=capability.session_id,
            speaker=Speaker.participant,
            ordinal=ordinal,
            display_text=participant_text,
            source_mode=InteractionMode.text,
            origin=TurnOrigin.study_api_text,
            recorded_at=body.client_created_at or now,
            client_message_id=body.client_message_id,
        )

        ai_count = await db.execute(
            text(
                """
                SELECT COUNT(*) FROM canonical_turns
                WHERE session_id = :session_id
                  AND speaker = 'ai'
                  AND origin = 'study_api_text'
                """
            ),
            {"session_id": capability.session_id},
        )
        ai_index = int(ai_count.scalar_one())
        replies = snapshot.scripted_ai_replies
        ai_text = replies[ai_index % len(replies)]
        ai_turn_id = _new_uuid7()
        ai_recorded_at = utc_now()
        await db.execute(
            text(
                """
                INSERT INTO canonical_turns (
                    turn_id, session_id, ordinal, speaker, origin,
                    verification_status, source_mode, display_text,
                    interrupted, content_hash, recorded_at, schema_version
                ) VALUES (
                    :turn_id, :session_id, :ordinal, :speaker, :origin,
                    'verified', :source_mode, :display_text,
                    false, :content_hash, :recorded_at, 1
                )
                """
            ),
            {
                "turn_id": ai_turn_id,
                "session_id": capability.session_id,
                "ordinal": ordinal + 1,
                "speaker": Speaker.ai.value,
                "origin": TurnOrigin.study_api_text.value,
                "source_mode": InteractionMode.text.value,
                "display_text": ai_text,
                "content_hash": _turn_content_hash(ai_text),
                "recorded_at": ai_recorded_at,
            },
        )
        ai_turn = TurnRecord(
            turn_id=ai_turn_id,
            session_id=capability.session_id,
            speaker=Speaker.ai,
            ordinal=ordinal + 1,
            display_text=ai_text,
            source_mode=InteractionMode.text,
            origin=TurnOrigin.study_api_text,
            recorded_at=ai_recorded_at,
        )

        result = await db.execute(
            text(
                """
                UPDATE sessions
                SET version = version + 1,
                    writer_lease_expires_at = :expires_at,
                    updated_at = now()
                WHERE session_id = :session_id AND version = :expected_version
                RETURNING version, status
                """
            ),
            {
                "expires_at": utc_now() + WRITER_LEASE_DURATION,
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            },
        )
        row = result.mappings().first()
        if row is None:
            await _pg_version_conflict(db, capability.session_id)
        await db.commit()
        new_version = row["version"]
        new_status = SessionStatus(row["status"])

    response = MessageResponse(
        operation_id=_new_uuid7(),
        operation_status=GenerationOperationStatus.succeeded,
        participant_turn=_turn_to_view(participant_turn),
        ai_turn=_turn_to_view(ai_turn),
        status=new_status,
        version=new_version,
    )
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response


async def _pg_record_observations(
    capability: CapabilityContext,
    body: ObservationBatchCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ObservationBatchResponse:
    scope = _pg_idempotency_scope("observations")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ObservationBatchResponse.model_validate(cached)

    async with _pg_session() as db:
        record, _snapshot = await _pg_load_session_bundle(db, capability.session_id)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)

        for observation in body.observations:
            await db.execute(
                text(
                    """
                    INSERT INTO observations (
                        observation_id, session_id, observation_type, occurred_at,
                        connection_state, client_first_audio_observed_ms,
                        client_first_transcript_observed_ms
                    ) VALUES (
                        :observation_id, :session_id, :observation_type, :occurred_at,
                        :connection_state, :client_first_audio_observed_ms,
                        :client_first_transcript_observed_ms
                    )
                    ON CONFLICT (observation_id) DO NOTHING
                    """
                ),
                {
                    "observation_id": observation.observation_id,
                    "session_id": capability.session_id,
                    "observation_type": observation.observation_type.value,
                    "occurred_at": observation.occurred_at,
                    "connection_state": (
                        observation.connection_state.value
                        if observation.connection_state is not None
                        else None
                    ),
                    "client_first_audio_observed_ms": (
                        observation.client_first_audio_observed_ms
                    ),
                    "client_first_transcript_observed_ms": (
                        observation.client_first_transcript_observed_ms
                    ),
                },
            )

        result = await db.execute(
            text(
                """
                UPDATE sessions
                SET version = version + 1,
                    writer_lease_expires_at = :expires_at,
                    updated_at = now()
                WHERE session_id = :session_id AND version = :expected_version
                RETURNING version
                """
            ),
            {
                "expires_at": utc_now() + WRITER_LEASE_DURATION,
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            },
        )
        row = result.mappings().first()
        if row is None:
            await _pg_version_conflict(db, capability.session_id)
        await db.commit()
        new_version = row["version"]

    acks = [
        ObservationAck(
            accepted=True,
            observation_id=obs.observation_id,
            untrusted=True,
        )
        for obs in body.observations
    ]
    response = ObservationBatchResponse(accepted=acks, version=new_version)
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response


async def _pg_get_transcript(capability: CapabilityContext) -> TranscriptResponse:
    async with _pg_session() as db:
        record, _ = await _pg_load_session_bundle(db, capability.session_id)
        turns = await _pg_list_turns(db, capability.session_id)
    return TranscriptResponse(
        version=record.version,
        turns=[_turn_to_view(turn) for turn in turns],
    )


async def _pg_complete_session(
    capability: CapabilityContext,
    body: SessionCompleteRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> SessionCompleteResponse:
    scope = _pg_idempotency_scope("complete")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return SessionCompleteResponse.model_validate(cached)

    async with _pg_session() as db:
        result = await db.execute(
            text("SELECT * FROM sessions WHERE session_id = :session_id FOR UPDATE"),
            {"session_id": capability.session_id},
        )
        row = result.mappings().first()
        if row is None:
            raise StudyApiError(
                status_code=404,
                error_code="session_not_found",
                message="Session not found",
            )
        from app.repositories.sessions import SessionRepository

        record = SessionRepository._row_to_record(row)
        snapshot_row = await db.execute(
            text(
                "SELECT * FROM configuration_snapshots "
                "WHERE configuration_snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": record.configuration_snapshot_id},
        )
        snap = snapshot_row.mappings().first()
        if snap is None:
            raise StudyApiError(
                status_code=500,
                error_code="internal_error",
                message="Configuration snapshot missing",
            )
        from app.repositories._types import ConfigurationSnapshotRecord

        snapshot = _snapshot_config_from_record(
            ConfigurationSnapshotRecord(
                configuration_snapshot_id=snap["configuration_snapshot_id"],
                study_id=snap["study_id"],
                study_wave=snap["study_wave"],
                protocol_version=snap["protocol_version"],
                issue_version=snap["issue_version"],
                persona_version=snap["persona_version"],
                prompt_content_hash=snap["prompt_content_hash"],
                prompt_object_reference=snap["prompt_object_reference"],
                opening_display_text=snap["opening_display_text"],
                ai_speaks_first=snap["ai_speaks_first"],
                model_provider=snap["model_provider"],
                model_name=snap["model_name"],
                model_parameters_json=snap["model_parameters_json"],
                voice_config_json=snap["voice_config_json"],
                tool_manifest_hash=snap["tool_manifest_hash"],
                safety_policy_version=snap["safety_policy_version"],
                assignment_seed_reference=snap["assignment_seed_reference"],
                application_version=snap["application_version"],
            )
        )

        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)

        for observation in body.recovery_observations:
            await db.execute(
                text(
                    """
                    INSERT INTO observations (
                        observation_id, session_id, observation_type, occurred_at,
                        connection_state, client_first_audio_observed_ms,
                        client_first_transcript_observed_ms
                    ) VALUES (
                        :observation_id, :session_id, :observation_type, :occurred_at,
                        :connection_state, :client_first_audio_observed_ms,
                        :client_first_transcript_observed_ms
                    )
                    ON CONFLICT (observation_id) DO NOTHING
                    """
                ),
                {
                    "observation_id": observation.observation_id,
                    "session_id": capability.session_id,
                    "observation_type": observation.observation_type.value,
                    "occurred_at": observation.occurred_at,
                    "connection_state": (
                        observation.connection_state.value
                        if observation.connection_state is not None
                        else None
                    ),
                    "client_first_audio_observed_ms": (
                        observation.client_first_audio_observed_ms
                    ),
                    "client_first_transcript_observed_ms": (
                        observation.client_first_transcript_observed_ms
                    ),
                },
            )

        now = utc_now()
        complete_result = await db.execute(
            text(
                """
                UPDATE sessions
                SET status = 'completed',
                    completion_reason = :completion_reason,
                    completed_at = :completed_at,
                    version = version + 1,
                    writer_lease_id = NULL,
                    writer_lease_expires_at = NULL,
                    updated_at = now()
                WHERE session_id = :session_id
                  AND version = :expected_version
                  AND status IN ('active', 'paused')
                RETURNING *
                """
            ),
            {
                "completion_reason": body.reason,
                "completed_at": now,
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            },
        )
        completed_row = complete_result.mappings().first()
        if completed_row is None:
            await _pg_version_conflict(db, capability.session_id)
        await db.commit()
        record = SessionRepository._row_to_record(completed_row)
        turn_count = await _pg_count_turns(db, capability.session_id)

    response = SessionCompleteResponse(
        session=_project_session_from_parts(record, snapshot, capability.writer_role),
        saved_turn_count=turn_count,
    )
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, response.model_dump()
    )
    from app.services.tracing import SessionDomain, get_tracing_service

    get_tracing_service().on_session_completed(
        SessionDomain(record=record, snapshot=snapshot)
    )
    return response


async def _pg_pause_session(
    capability: CapabilityContext,
    body: SessionPauseRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
    scope = _pg_idempotency_scope("pause")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ParticipantSessionView.model_validate(cached)

    async with _pg_session() as db:
        record, snapshot = await _pg_load_session_bundle(db, capability.session_id)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)
        if not snapshot.rules.allow_resume:
            raise StudyApiError(
                status_code=409,
                error_code="session_not_started",
                message="Pause is not allowed for this session",
            )
        if record.status != SessionStatus.active:
            raise StudyApiError(
                status_code=409,
                error_code="session_not_started",
                message="Only active sessions can be paused",
                session_status=record.status.value,
            )
        result = await db.execute(
            text(
                """
                UPDATE sessions
                SET status = 'paused', version = version + 1, updated_at = now()
                WHERE session_id = :session_id AND version = :expected_version
                RETURNING *
                """
            ),
            {
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            },
        )
        row = result.mappings().first()
        if row is None:
            await _pg_version_conflict(db, capability.session_id)
        await db.commit()
        from app.repositories.sessions import SessionRepository

        record = SessionRepository._row_to_record(row)

    view = _project_session_from_parts(record, snapshot, capability.writer_role)
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, view.model_dump()
    )
    return view


async def _pg_transfer_writer_lease(
    capability: CapabilityContext,
    body: WriterLeaseTransferRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
    scope = _pg_idempotency_scope("transfer")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return ParticipantSessionView.model_validate(cached)

    nonces = _pg_transfer_nonces.get(capability.session_id, {})
    if body.transfer_nonce not in nonces:
        async with _pg_session() as db:
            record, _ = await _pg_load_session_bundle(db, capability.session_id)
        raise StudyApiError(
            status_code=409,
            error_code="writer_conflict",
            message="Invalid transfer nonce",
            current_version=record.version,
        )

    async with _pg_session() as db:
        record, snapshot = await _pg_load_session_bundle(db, capability.session_id)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)
        now = utc_now()
        lease_id = _new_uuid7()
        result = await db.execute(
            text(
                """
                UPDATE sessions
                SET writer_lease_id = :lease_id,
                    writer_lease_expires_at = :expires_at,
                    version = version + 1,
                    updated_at = now()
                WHERE session_id = :session_id AND version = :expected_version
                RETURNING *
                """
            ),
            {
                "lease_id": lease_id,
                "expires_at": now + WRITER_LEASE_DURATION,
                "session_id": capability.session_id,
                "expected_version": body.expected_version,
            },
        )
        row = result.mappings().first()
        if row is None:
            await _pg_version_conflict(db, capability.session_id)
        await db.commit()
        from app.repositories.sessions import SessionRepository

        record = SessionRepository._row_to_record(row)

    view = _project_session_from_parts(record, snapshot, "writer")
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, view.model_dump()
    )
    return view


async def _pg_create_realtime_call(
    capability: CapabilityContext,
    body: RealtimeCallCreateRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> RealtimeCallCreateResponse:
    scope = _pg_idempotency_scope("realtime")
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return RealtimeCallCreateResponse.model_validate(cached)

    async with _pg_session() as db:
        record, snapshot = await _pg_load_session_bundle(db, capability.session_id)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)
        _pg_check_consent(record, snapshot)
        if record.status != SessionStatus.active:
            raise StudyApiError(
                status_code=409,
                error_code="session_not_started",
                message="Session must be active for realtime setup",
            )
        await db.execute(
            text(
                """
                UPDATE sessions
                SET writer_lease_expires_at = :expires_at, updated_at = now()
                WHERE session_id = :session_id
                """
            ),
            {
                "expires_at": utc_now() + WRITER_LEASE_DURATION,
                "session_id": capability.session_id,
            },
        )
        await db.commit()

    response = RealtimeCallCreateResponse(
        sdp_answer=FAKE_SDP_ANSWER,
        expires_at=utc_now() + timedelta(minutes=5),
    )
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response


def build_demo_configuration_snapshot_record(
    *, study_id: UUID, snapshot_id: UUID | None = None
) -> "ConfigurationSnapshotRecord":
    from app.repositories._types import ConfigurationSnapshotRecord

    return ConfigurationSnapshotRecord(
        configuration_snapshot_id=snapshot_id or _new_uuid7(),
        study_id=study_id,
        study_wave=DEMO_STUDY_WAVE,
        protocol_version=DEMO_PROMPT_VERSION,
        issue_version=DEMO_ISSUE.issue_id,
        persona_version="v1",
        prompt_content_hash="demo-v1",
        prompt_object_reference="prompts/demo-v1.json",
        opening_display_text=DEMO_OPENING_MESSAGE,
        ai_speaks_first=True,
        model_provider="openai",
        model_name="gpt-4.1-mini",
        tool_manifest_hash="tools-v1",
        safety_policy_version="safety-v1",
        assignment_seed_reference="seed-001",
        application_version="test",
    )


async def seed_postgres_invitation(invitation_token: str) -> UUID:
    from app.repositories.invitations import DEFAULT_STUDY_ID, InvitationRepository

    async with _pg_session() as db:
        repo = InvitationRepository(db)
        snapshot = build_demo_configuration_snapshot_record(study_id=DEFAULT_STUDY_ID)
        invitation = await repo.create_invitation(
            invitation_token=invitation_token,
            study_id=DEFAULT_STUDY_ID,
            configuration_snapshot=snapshot,
        )
        return invitation.session_id
