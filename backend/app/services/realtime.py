import hashlib
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.openai_realtime import (
    RealtimeCallResult,
    get_configured_realtime_model,
    get_realtime_client,
)
from app.models.enums import InteractionMode, SessionStatus, Speaker, TurnOrigin
from app.models.realtime import (
    RealtimeCallCreateRequest,
    RealtimeCallCreateResponse,
    RealtimeProviderItemIngest,
    RealtimeProviderItemIngestResponse,
)
from app.models.transcript import TurnRecord
from app.repositories.realtime_calls import RealtimeCallRecord, RealtimeCallRepository
from app.repositories.turns import TurnRepository
from app.sample_data.sessions import ConfigurationSnapshot
from app.services.sessions import (
    CapabilityContext,
    StudyApiError,
    WRITER_LEASE_DURATION,
    _check_consent,
    _check_idempotency,
    _check_version,
    _ensure_writable,
    _get_state,
    _idempotency_scope,
    _new_uuid7,
    _pg_check_consent,
    _pg_check_idempotency,
    _pg_check_version,
    _pg_count_turns,
    _pg_ensure_writable,
    _pg_idempotency_scope,
    _pg_list_turns,
    _pg_load_session_bundle,
    _pg_session,
    _pg_store_idempotency,
    _renew_writer_lease,
    _run_async,
    _snapshot_config_from_record,
    _store_idempotency,
    _turn_content_hash,
    utc_now,
)

REALTIME_SETUPS_PER_SESSION = 10
REALTIME_SETUP_ATTEMPTS_PER_WINDOW = 10
REALTIME_SETUP_WINDOW = timedelta(minutes=5)
REALTIME_CALL_EXPIRY = timedelta(minutes=5)


@dataclass(frozen=True)
class ControlHandoff:
    realtime_call_id: UUID
    openai_call_id: str
    session_id: UUID


_memory_calls_by_openai_id: dict[str, RealtimeCallRecord] = {}
_memory_active_by_session: dict[UUID, str] = {}
_memory_setup_attempts: dict[str, list] = {}
_memory_session_setup_count: dict[UUID, int] = {}
_memory_turns_by_provider_item: dict[tuple[UUID, str], UUID] = {}
_control_handoff_queue: list[ControlHandoff] = []


def reset_memory_realtime_state() -> None:
    _memory_calls_by_openai_id.clear()
    _memory_active_by_session.clear()
    _memory_setup_attempts.clear()
    _memory_session_setup_count.clear()
    _memory_turns_by_provider_item.clear()
    _control_handoff_queue.clear()


def get_memory_openai_call_id_for_session(session_id: UUID) -> str | None:
    return _memory_active_by_session.get(session_id)


def drain_control_handoff_queue() -> list[ControlHandoff]:
    items = list(_control_handoff_queue)
    _control_handoff_queue.clear()
    return items


def _postgres_enabled() -> bool:
    return get_settings().use_postgres


def _safety_identifier(telemetry_thread_id: UUID) -> str:
    return hashlib.sha256(str(telemetry_thread_id).encode("utf-8")).hexdigest()


def _build_instructions(
    snapshot: ConfigurationSnapshot, turns: list[TurnRecord]
) -> str:
    parts = [
        f"You are {snapshot.ai_persona.display_name}, an AI participant in a research study.",
        snapshot.ai_persona.assigned_position,
        f"Issue: {snapshot.issue.title}",
        snapshot.issue.summary,
    ]
    if snapshot.rules.ai_speaks_first:
        for turn in turns:
            if turn.origin == TurnOrigin.snapshot_opening:
                parts.append(
                    "You have already greeted the participant with: "
                    f"{turn.display_text}"
                )
                break
    return "\n\n".join(parts)


def _build_realtime_session_config(
    snapshot: ConfigurationSnapshot, turns: list[TurnRecord]
) -> dict[str, object]:
    model = getattr(snapshot, "model_name", None) or get_configured_realtime_model()
    return {
        "type": "realtime",
        "model": model,
        "instructions": _build_instructions(snapshot, turns),
        "modalities": ["audio", "text"],
        "turn_detection": {"type": "server_vad"},
    }


def _rate_limit_error(retry_after_seconds: int = 60) -> StudyApiError:
    return StudyApiError(
        status_code=429,
        error_code="rate_limited",
        message="Realtime setup rate limit exceeded",
        retryable=True,
    )


def _check_memory_rate_limits(capability: CapabilityContext, session_id: UUID) -> None:
    now = utc_now()
    window_start = now - REALTIME_SETUP_WINDOW
    attempts = _memory_setup_attempts.setdefault(capability.capability_id, [])
    attempts[:] = [ts for ts in attempts if ts >= window_start]
    if len(attempts) >= REALTIME_SETUP_ATTEMPTS_PER_WINDOW:
        raise _rate_limit_error()
    attempts.append(now)

    setup_count = _memory_session_setup_count.get(session_id, 0)
    if setup_count >= REALTIME_SETUPS_PER_SESSION:
        raise _rate_limit_error()


async def _check_pg_rate_limits(
    db: AsyncSession, capability: CapabilityContext, session_id: UUID
) -> None:
    now = utc_now()
    window_start = now - REALTIME_SETUP_WINDOW
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM realtime_calls
            WHERE capability_id = :capability_id
              AND created_at >= :window_start
            """
        ),
        {
            "capability_id": capability.capability_id,
            "window_start": window_start,
        },
    )
    if int(result.scalar_one()) >= REALTIME_SETUP_ATTEMPTS_PER_WINDOW:
        raise _rate_limit_error()

    repo = RealtimeCallRepository(db)
    if await repo.count_successful_setups(session_id) >= REALTIME_SETUPS_PER_SESSION:
        raise _rate_limit_error()


def _enqueue_control_handoff(record: RealtimeCallRecord) -> None:
    _control_handoff_queue.append(
        ControlHandoff(
            realtime_call_id=record.realtime_call_id,
            openai_call_id=record.openai_call_id,
            session_id=record.session_id,
        )
    )


def _invalidate_memory_active_call(session_id: UUID, *, invalidated_at) -> None:
    active_call_id = _memory_active_by_session.pop(session_id, None)
    if active_call_id is None:
        return
    existing = _memory_calls_by_openai_id.get(active_call_id)
    if existing is None:
        return
    _memory_calls_by_openai_id[active_call_id] = existing.model_copy(
        update={"status": "invalidated", "invalidated_at": invalidated_at}
    )


def _persist_memory_call(
    *,
    session_id: UUID,
    capability_id: str,
    provider_result: RealtimeCallResult,
    expires_at,
) -> RealtimeCallRecord:
    now = utc_now()
    _invalidate_memory_active_call(session_id, invalidated_at=now)
    record = RealtimeCallRecord(
        realtime_call_id=_new_uuid7(),
        session_id=session_id,
        openai_call_id=provider_result.openai_call_id,
        capability_id=capability_id,
        status="active",
        expires_at=expires_at,
        control_handoff_enqueued_at=now,
    )
    _memory_calls_by_openai_id[provider_result.openai_call_id] = record
    _memory_active_by_session[session_id] = provider_result.openai_call_id
    _memory_session_setup_count[session_id] = (
        _memory_session_setup_count.get(session_id, 0) + 1
    )
    _enqueue_control_handoff(record)
    return record


def create_realtime_call(
    capability: CapabilityContext,
    body: RealtimeCallCreateRequest,
    *,
    idempotency_key: str,
    request_hash: str,
) -> RealtimeCallCreateResponse:
    if _postgres_enabled():
        return _run_async(
            _pg_create_realtime_call(
                capability,
                body,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        )
    return _memory_create_realtime_call(
        capability,
        body,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )


def _memory_create_realtime_call(
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

    _check_memory_rate_limits(capability, capability.session_id)

    session_config = _build_realtime_session_config(state.snapshot, state.turns)
    provider_result = get_realtime_client().create_call(
        sdp_offer=body.sdp_offer,
        session_config=session_config,
        safety_identifier=_safety_identifier(state.record.telemetry_thread_id),
    )
    expires_at = utc_now() + REALTIME_CALL_EXPIRY
    _persist_memory_call(
        session_id=capability.session_id,
        capability_id=capability.capability_id,
        provider_result=provider_result,
        expires_at=expires_at,
    )
    _renew_writer_lease(state)

    response = RealtimeCallCreateResponse(
        sdp_answer=provider_result.sdp_answer,
        expires_at=expires_at,
    )
    _store_idempotency(
        state, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response


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
        record, snapshot_record = await _pg_load_session_bundle(db, capability.session_id)
        snapshot = _snapshot_config_from_record(snapshot_record)
        _pg_ensure_writable(record, capability)
        _pg_check_version(record, body.expected_version)
        _pg_check_consent(record, snapshot)
        if record.status != SessionStatus.active:
            raise StudyApiError(
                status_code=409,
                error_code="session_not_started",
                message="Session must be active for realtime setup",
            )
        await _check_pg_rate_limits(db, capability, capability.session_id)

        turns = await _pg_list_turns(db, capability.session_id)
        session_config = _build_realtime_session_config(snapshot, turns)
        provider_result = get_realtime_client().create_call(
            sdp_offer=body.sdp_offer,
            session_config=session_config,
            safety_identifier=_safety_identifier(record.telemetry_thread_id),
        )
        expires_at = utc_now() + REALTIME_CALL_EXPIRY
        now = utc_now()
        call_repo = RealtimeCallRepository(db)
        await call_repo.invalidate_active_for_session(
            capability.session_id, invalidated_at=now
        )
        call_record = RealtimeCallRecord(
            realtime_call_id=_new_uuid7(),
            session_id=capability.session_id,
            openai_call_id=provider_result.openai_call_id,
            capability_id=capability.capability_id,
            status="active",
            expires_at=expires_at,
            control_handoff_enqueued_at=now,
        )
        await call_repo.create(call_record)
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
        _enqueue_control_handoff(call_record)

    response = RealtimeCallCreateResponse(
        sdp_answer=provider_result.sdp_answer,
        expires_at=expires_at,
    )
    _pg_store_idempotency(
        capability.session_id, scope, idempotency_key, request_hash, response.model_dump()
    )
    return response


def ingest_provider_item(
    openai_call_id: str,
    body: RealtimeProviderItemIngest,
) -> RealtimeProviderItemIngestResponse:
    if _postgres_enabled():
        return _run_async(_pg_ingest_provider_item(openai_call_id, body))
    return _memory_ingest_provider_item(openai_call_id, body)


def _memory_ingest_provider_item(
    openai_call_id: str,
    body: RealtimeProviderItemIngest,
) -> RealtimeProviderItemIngestResponse:
    call = _memory_calls_by_openai_id.get(openai_call_id)
    if call is None:
        raise StudyApiError(
            status_code=404,
            error_code="session_not_found",
            message="Realtime call not found",
        )

    existing_turn_id = _memory_turns_by_provider_item.get(
        (call.session_id, body.provider_item_id)
    )
    if existing_turn_id is not None:
        return RealtimeProviderItemIngestResponse(
            turn_id=existing_turn_id,
            created=False,
        )

    state = _get_state(call.session_id)
    turn_id = _new_uuid7()
    ordinal = len(state.turns)
    now = utc_now()
    turn = TurnRecord(
        turn_id=turn_id,
        session_id=call.session_id,
        speaker=Speaker.ai,
        ordinal=ordinal,
        display_text=body.display_text,
        source_mode=InteractionMode.voice,
        origin=TurnOrigin.provider_realtime,
        interrupted=body.interrupted,
        recorded_at=now,
    )
    state.turns.append(turn)
    _memory_turns_by_provider_item[(call.session_id, body.provider_item_id)] = turn_id
    return RealtimeProviderItemIngestResponse(turn_id=turn_id, created=True)


async def _pg_ingest_provider_item(
    openai_call_id: str,
    body: RealtimeProviderItemIngest,
) -> RealtimeProviderItemIngestResponse:
    async with _pg_session() as db:
        call_repo = RealtimeCallRepository(db)
        call = await call_repo.get_by_openai_call_id(openai_call_id)
        if call is None:
            raise StudyApiError(
                status_code=404,
                error_code="session_not_found",
                message="Realtime call not found",
            )

        turn_repo = TurnRepository(db)
        existing = await turn_repo._get_by_provider_item_id(
            call.session_id, body.provider_item_id
        )
        if existing is not None:
            return RealtimeProviderItemIngestResponse(
                turn_id=existing.turn_id,
                created=False,
            )

        ordinal = await _pg_count_turns(db, call.session_id)
        turn_id = _new_uuid7()
        now = utc_now()
        inserted = await turn_repo.insert_turn(
            turn_id=turn_id,
            session_id=call.session_id,
            ordinal=ordinal,
            speaker=Speaker.ai,
            origin=TurnOrigin.provider_realtime,
            source_mode=InteractionMode.voice,
            display_text=body.display_text,
            content_hash=_turn_content_hash(body.display_text),
            recorded_at=now,
            interrupted=body.interrupted,
            provider_item_id=body.provider_item_id,
            provider_response_id=body.provider_response_id,
            provider_created_at=body.provider_created_at,
        )
        return RealtimeProviderItemIngestResponse(
            turn_id=inserted.turn_id,
            created=True,
        )
