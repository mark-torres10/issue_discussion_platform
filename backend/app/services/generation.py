from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.core.config import get_settings
from app.integrations.openai_client import (
    generate_chat_completion,
    get_configured_text_model,
    get_openai_client,
)
from app.models.enums import (
    GenerationOperationStatus,
    InteractionMode,
    SessionStatus,
    Speaker,
    TurnOrigin,
)
from app.models.generation import GenerationOperation
from app.models.transcript import MessageCreate, MessageResponse, TurnRecord
from app.repositories.generation_operations import GenerationOperationRepository
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
    _pg_load_session_bundle,
    _pg_session,
    _pg_store_idempotency,
    _pg_version_conflict,
    _renew_writer_lease,
    _run_async,
    _store_idempotency,
    _turn_content_hash,
    _turn_to_view,
    utc_now,
)
from app.sample_data.sessions import ConfigurationSnapshot

MESSAGES_SCOPE = "messages"
DEFAULT_MEMORY_MODEL = "gpt-4.1-mini"


class _MemoryGenerationOperation:
    def __init__(self, operation: GenerationOperation) -> None:
        self.operation = operation


_memory_operations: dict[tuple[UUID, str, str], _MemoryGenerationOperation] = {}


def reset_memory_generation_operations() -> None:
    _memory_operations.clear()


def _postgres_enabled() -> bool:
    return get_settings().use_postgres


def _memory_snapshot_model(snapshot: ConfigurationSnapshot) -> str:
    return getattr(snapshot, "model_name", DEFAULT_MEMORY_MODEL)


def _validate_snapshot_model(snapshot_model: str) -> None:
    configured = get_configured_text_model()
    if snapshot_model != configured:
        raise StudyApiError(
            status_code=409,
            error_code="validation_error",
            message="Snapshot model does not match configured text model",
        )


def _build_chat_messages(
  snapshot: ConfigurationSnapshot,
  turns: list[TurnRecord],
  participant_text: str,
) -> list[dict[str, str]]:
    system_parts = [
        f"You are {snapshot.ai_persona.display_name}, an AI participant in a research study.",
        snapshot.ai_persona.assigned_position,
        f"Issue: {snapshot.issue.title}",
        snapshot.issue.summary,
    ]
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "\n\n".join(system_parts)},
    ]
    for turn in turns:
        if turn.speaker == Speaker.participant:
            messages.append({"role": "user", "content": turn.display_text})
        elif turn.speaker == Speaker.ai:
            messages.append({"role": "assistant", "content": turn.display_text})
    messages.append({"role": "user", "content": participant_text})
    return messages


def _openai_failure(exc: Exception) -> StudyApiError:
    return StudyApiError(
        status_code=503,
        error_code="generation_failed",
        message="Text generation failed",
        retryable=True,
    )


def create_message(
    capability: CapabilityContext,
    body: MessageCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> MessageResponse:
    if _postgres_enabled():
        return _run_async(
            _pg_create_message(
                capability,
                body,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        )
    return _memory_create_message(
        capability,
        body,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )


def _memory_get_operation(
    session_id: UUID, scope: str, key: str
) -> GenerationOperation | None:
    record = _memory_operations.get((session_id, scope, key))
    if record is None:
        return None
    return record.operation


def _memory_store_operation(operation: GenerationOperation) -> None:
    _memory_operations[
        (operation.session_id, operation.idempotency_scope, operation.idempotency_key)
    ] = _MemoryGenerationOperation(operation)


def _memory_create_message(
    capability: CapabilityContext,
    body: MessageCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> MessageResponse:
    state = _get_state(capability.session_id)
    scope = _idempotency_scope(MESSAGES_SCOPE)
    cached = _check_idempotency(
        state, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return MessageResponse.model_validate(cached)

    existing_operation = _memory_get_operation(capability.session_id, scope, idempotency_key)
    if existing_operation is not None:
        if existing_operation.request_hash != request_hash:
            raise StudyApiError(
                status_code=409,
                error_code="idempotency_conflict",
                message="Idempotency key reused with different request body",
                current_version=state.record.version,
            )
        if existing_operation.status == GenerationOperationStatus.succeeded:
            if existing_operation.response_body is not None:
                return MessageResponse.model_validate(existing_operation.response_body)
        if existing_operation.status == GenerationOperationStatus.failed:
            raise _openai_failure(RuntimeError("stored generation failure"))

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

    snapshot_model = _memory_snapshot_model(state.snapshot)
    _validate_snapshot_model(snapshot_model)

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

    operation_id = _new_uuid7()
    operation = GenerationOperation(
        operation_id=operation_id,
        session_id=capability.session_id,
        idempotency_scope=scope,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status=GenerationOperationStatus.accepted,
        participant_turn_id=participant_turn.turn_id,
        model_name=snapshot_model,
        created_at=now,
        updated_at=now,
    )
    _memory_store_operation(operation)

    operation = operation.model_copy(
        update={"status": GenerationOperationStatus.running, "updated_at": utc_now()}
    )
    _memory_store_operation(operation)

    try:
        client = get_openai_client()
        ai_text = generate_chat_completion(
            client=client,
            model=snapshot_model,
            messages=_build_chat_messages(state.snapshot, state.turns[:-1], body.text),
        )
    except Exception as exc:
        failed = operation.model_copy(
            update={
                "status": GenerationOperationStatus.failed,
                "error_code": "generation_failed",
                "error_message": str(exc),
                "updated_at": utc_now(),
            }
        )
        _memory_store_operation(failed)
        raise _openai_failure(exc) from exc

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

    response = MessageResponse(
        operation_id=operation_id,
        operation_status=GenerationOperationStatus.succeeded,
        participant_turn=_turn_to_view(participant_turn),
        ai_turn=_turn_to_view(ai_turn),
        status=state.record.status,
        version=state.record.version,
    )

    succeeded = operation.model_copy(
        update={
            "status": GenerationOperationStatus.succeeded,
            "ai_turn_id": ai_turn.turn_id,
            "response_body": response.model_dump(mode="json"),
            "updated_at": utc_now(),
        }
    )
    _memory_store_operation(succeeded)
    _store_idempotency(
        state, scope, idempotency_key, request_hash, response.model_dump(mode="json")
    )
    from app.services.tracing import get_tracing_service, session_domain_from_memory

    domain = session_domain_from_memory(capability.session_id)
    succeeded_op = _memory_get_operation(capability.session_id, scope, idempotency_key)
    if succeeded_op is not None:
        get_tracing_service().on_generation_committed(
            domain,
            participant_turn,
            ai_turn,
            succeeded_op,
        )
    return response


async def _pg_create_message(
    capability: CapabilityContext,
    body: MessageCreate,
    *,
    idempotency_key: str,
    request_hash: str,
) -> MessageResponse:
    scope = _pg_idempotency_scope(MESSAGES_SCOPE)
    cached = _pg_check_idempotency(
        capability.session_id, scope=scope, key=idempotency_key, request_hash=request_hash
    )
    if cached is not None:
        return MessageResponse.model_validate(cached)

    async with _pg_session() as db:
        gen_repo = GenerationOperationRepository(db)
        existing_operation = await gen_repo.get_by_idempotency(
            capability.session_id, scope=scope, key=idempotency_key
        )
        if existing_operation is not None:
            if existing_operation.request_hash != request_hash:
                raise StudyApiError(
                    status_code=409,
                    error_code="idempotency_conflict",
                    message="Idempotency key reused with different request body",
                )
            if existing_operation.status == GenerationOperationStatus.succeeded:
                if existing_operation.response_body is not None:
                    return MessageResponse.model_validate(existing_operation.response_body)
            if existing_operation.status == GenerationOperationStatus.failed:
                raise _openai_failure(RuntimeError("stored generation failure"))

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

        snapshot_row = await db.execute(
            text(
                "SELECT model_name FROM configuration_snapshots "
                "WHERE configuration_snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": record.configuration_snapshot_id},
        )
        snap_model_row = snapshot_row.mappings().first()
        if snap_model_row is None:
            raise StudyApiError(
                status_code=500,
                error_code="internal_error",
                message="Configuration snapshot missing",
            )
        snapshot_model = snap_model_row["model_name"]
        _validate_snapshot_model(snapshot_model)

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

        operation_id = _new_uuid7()
        await gen_repo.create_accepted(
            session_id=capability.session_id,
            scope=scope,
            key=idempotency_key,
            request_hash=request_hash,
            model_name=snapshot_model,
            participant_turn_id=participant_turn_id,
            operation_id=operation_id,
        )
        await gen_repo.update_status(
            operation_id, status=GenerationOperationStatus.running
        )

        prior_turns = await _pg_list_turn_records(db, capability.session_id)
        prior_turns = [turn for turn in prior_turns if turn.turn_id != participant_turn_id]

        try:
            client = get_openai_client()
            ai_text = generate_chat_completion(
                client=client,
                model=snapshot_model,
                messages=_build_chat_messages(snapshot, prior_turns, body.text),
            )
        except Exception as exc:
            await gen_repo.update_status(
                operation_id,
                status=GenerationOperationStatus.failed,
                error_code="generation_failed",
                error_message=str(exc),
            )
            await db.commit()
            raise _openai_failure(exc) from exc

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

        response = MessageResponse(
            operation_id=operation_id,
            operation_status=GenerationOperationStatus.succeeded,
            participant_turn=_turn_to_view(participant_turn),
            ai_turn=_turn_to_view(ai_turn),
            status=SessionStatus(row["status"]),
            version=row["version"],
        )
        await gen_repo.update_status(
            operation_id,
            status=GenerationOperationStatus.succeeded,
            ai_turn_id=ai_turn_id,
            response_body=response.model_dump(mode="json"),
        )
        await db.commit()
        committed_op = await gen_repo.get_by_idempotency(
            capability.session_id, scope=scope, key=idempotency_key
        )
        if committed_op is not None:
            from app.services.tracing import (
                SessionDomain,
                get_tracing_service,
            )

            get_tracing_service().on_generation_committed(
                SessionDomain(record=record, snapshot=snapshot),
                participant_turn,
                ai_turn,
                committed_op,
            )

    _pg_store_idempotency(
        capability.session_id,
        scope,
        idempotency_key,
        request_hash,
        response.model_dump(mode="json"),
    )
    return response


async def _pg_list_turn_records(db: Any, session_id: UUID) -> list[TurnRecord]:
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
