import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

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
    ConfigurationSnapshot,
    INVITATION_TOKEN_HASHES,
    build_demo_session_record,
)

GRACE_PERIOD = timedelta(hours=24)
WRITER_LEASE_DURATION = timedelta(minutes=30)
FAKE_SDP_ANSWER = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=sample-contracts\r\n"


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
    state = _get_state(capability.session_id)
    return _project_session(state, capability.writer_role)


def record_consent(
    capability: CapabilityContext,
    body: ConsentRecordRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
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
    return response


def create_message(
    capability: CapabilityContext,
    body: MessageCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> MessageResponse:
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
    state = _get_state(capability.session_id)
    scope = _idempotency_scope("complete")
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
    return response


def pause_session(
    capability: CapabilityContext,
    body: SessionPauseRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> ParticipantSessionView:
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
