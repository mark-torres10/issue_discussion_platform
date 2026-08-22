"""Study API tracing hooks for LangSmith export."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core.config import get_settings
from app.integrations.langsmith_envelope import (
    build_connection_failure_envelope,
    build_lifecycle_envelope,
    build_text_generation_envelope,
    build_voice_turn_envelope,
)
from app.integrations.langsmith_exporter import TraceExporter, build_exporter
from app.models.enums import InteractionMode
from app.models.generation import GenerationOperation
from app.models.session import SessionRecord
from app.models.tracing import SessionEvent, TraceExportKind, TraceKind
from app.models.transcript import TurnRecord
from app.repositories.trace_runs import (
    memory_get_trace_run,
    memory_upsert_trace_run,
    reset_memory_trace_runs,
)
from app.sample_data.sessions import ConfigurationSnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionDomain:
    record: SessionRecord
    snapshot: ConfigurationSnapshot


class StudyTracingService(Protocol):
    def on_session_started(
        self,
        session: SessionDomain,
        *,
        preferred_mode: InteractionMode,
        opening_turn: TurnRecord | None = None,
    ) -> None: ...

    def on_generation_committed(
        self,
        session: SessionDomain,
        participant_turn: TurnRecord | None,
        ai_turn: TurnRecord,
        operation: GenerationOperation,
    ) -> None: ...

    def on_voice_turn_committed(
        self,
        session: SessionDomain,
        ai_turn: TurnRecord,
        *,
        trace_kind: TraceKind,
        provider_response_id: str | None = None,
    ) -> None: ...

    def on_session_completed(self, session: SessionDomain) -> None: ...

    def on_connection_failure(
        self, session: SessionDomain, event: SessionEvent
    ) -> None: ...


_exporter_override: TraceExporter | None = None


def set_trace_exporter(exporter: TraceExporter | None) -> None:
    global _exporter_override
    _exporter_override = exporter


def reset_tracing_state() -> None:
    reset_memory_trace_runs()
    set_trace_exporter(None)


def _new_uuid7() -> UUID:
    from app.services.sessions import _new_uuid7 as sessions_new_uuid7

    return sessions_new_uuid7()


def _postgres_enabled() -> bool:
    return get_settings().use_postgres


def _run_async(coro):  # type: ignore[no-untyped-def]
    from app.services.sessions import _run_async as sessions_run_async

    return sessions_run_async(coro)


def _get_exporter() -> TraceExporter:
    if _exporter_override is not None:
        return _exporter_override
    settings = get_settings()
    return build_exporter(
        enabled=settings.trace_export_enabled,
        project_name=settings.langsmith_project,
    )


def _resolve_root_run_id(
    *,
    session_id: UUID,
    canonical_turn_id: UUID | None,
    export_kind: TraceExportKind,
    trace_kind: TraceKind | None = None,
) -> UUID:
    if canonical_turn_id is not None:
        if _postgres_enabled():
            return _run_async(
                _pg_resolve_root_run_id(
                    session_id=session_id,
                    canonical_turn_id=canonical_turn_id,
                    export_kind=export_kind,
                    trace_kind=trace_kind,
                )
            )
        existing = memory_get_trace_run(canonical_turn_id, export_kind=export_kind)
        if existing is not None:
            return existing.langsmith_root_run_id
        run_id = _new_uuid7()
        memory_upsert_trace_run(
            session_id=session_id,
            export_kind=export_kind,
            langsmith_root_run_id=run_id,
            canonical_turn_id=canonical_turn_id,
            trace_kind=trace_kind,
        )
        return run_id
    return _new_uuid7()


async def _pg_resolve_root_run_id(
    *,
    session_id: UUID,
    canonical_turn_id: UUID,
    export_kind: TraceExportKind,
    trace_kind: TraceKind | None,
) -> UUID:
    from app.repositories.trace_runs import TraceRunRepository
    from app.services.sessions import _pg_session

    async with _pg_session() as db:
        repo = TraceRunRepository(db)
        existing = await repo.get_by_canonical_turn(
            canonical_turn_id, export_kind=export_kind
        )
        if existing is not None:
            return existing.langsmith_root_run_id
        run_id = _new_uuid7()
        await repo.upsert(
            session_id=session_id,
            export_kind=export_kind,
            langsmith_root_run_id=run_id,
            canonical_turn_id=canonical_turn_id,
            trace_kind=trace_kind,
        )
        await db.commit()
        return run_id


def _safe_export(action: str, callback: object) -> None:
    try:
        callback()  # type: ignore[operator]
    except Exception:
        logger.exception("LangSmith export failed during %s", action)


class DefaultStudyTracingService:
    def on_session_started(
        self,
        session: SessionDomain,
        *,
        preferred_mode: InteractionMode,
        opening_turn: TurnRecord | None = None,
    ) -> None:
        if opening_turn is not None:
            # Opening snapshot text is canonical transcript only, not a generation trace.
            pass

        def _export() -> None:
            run_id = _new_uuid7()
            envelope = build_lifecycle_envelope(
                record=session.record,
                snapshot=session.snapshot,
                langsmith_run_id=run_id,
                lifecycle_event="session_started",
                interaction_mode=preferred_mode,
            )
            _get_exporter().export_lifecycle(
                envelope, lifecycle_event="session_started"
            )

        _safe_export("on_session_started", _export)

    def on_generation_committed(
        self,
        session: SessionDomain,
        participant_turn: TurnRecord | None,
        ai_turn: TurnRecord,
        operation: GenerationOperation,
    ) -> None:
        def _export() -> None:
            run_id = _resolve_root_run_id(
                session_id=session.record.session_id,
                canonical_turn_id=ai_turn.turn_id,
                export_kind=TraceExportKind.conversation_turn,
                trace_kind=TraceKind.instrumented_text_generation,
            )
            envelope = build_text_generation_envelope(
                record=session.record,
                snapshot=session.snapshot,
                participant_turn=participant_turn,
                ai_turn=ai_turn,
                operation=operation,
                langsmith_run_id=run_id,
            )
            _get_exporter().export_conversation_turn(envelope)

        _safe_export("on_generation_committed", _export)

    def on_voice_turn_committed(
        self,
        session: SessionDomain,
        ai_turn: TurnRecord,
        *,
        trace_kind: TraceKind,
        provider_response_id: str | None = None,
    ) -> None:
        def _export() -> None:
            run_id = _resolve_root_run_id(
                session_id=session.record.session_id,
                canonical_turn_id=ai_turn.turn_id,
                export_kind=TraceExportKind.conversation_turn,
                trace_kind=trace_kind,
            )
            envelope = build_voice_turn_envelope(
                record=session.record,
                snapshot=session.snapshot,
                ai_turn=ai_turn,
                trace_kind=trace_kind,
                langsmith_run_id=run_id,
                provider_response_id=provider_response_id,
            )
            _get_exporter().export_conversation_turn(envelope)

        _safe_export("on_voice_turn_committed", _export)

    def on_session_completed(self, session: SessionDomain) -> None:
        def _export() -> None:
            run_id = _new_uuid7()
            envelope = build_lifecycle_envelope(
                record=session.record,
                snapshot=session.snapshot,
                langsmith_run_id=run_id,
                lifecycle_event="session_completed",
            )
            _get_exporter().export_lifecycle(
                envelope, lifecycle_event="session_completed"
            )

        _safe_export("on_session_completed", _export)

    def on_connection_failure(
        self, session: SessionDomain, event: SessionEvent
    ) -> None:
        def _export() -> None:
            run_id = _new_uuid7()
            envelope = build_connection_failure_envelope(
                record=session.record,
                snapshot=session.snapshot,
                langsmith_run_id=run_id,
                event_type=event.event_type,
                error_code=event.error_code,
            )
            _get_exporter().export_connection_failure(
                envelope, event_type=event.event_type
            )

        _safe_export("on_connection_failure", _export)


_tracing_service: StudyTracingService = DefaultStudyTracingService()


def get_tracing_service() -> StudyTracingService:
    return _tracing_service


def session_domain_from_memory(session_id: UUID) -> SessionDomain:
    from app.services.sessions import _get_state

    state = _get_state(session_id)
    return SessionDomain(record=state.record, snapshot=state.snapshot)


def session_domain_from_postgres(session_id: UUID) -> SessionDomain:
    from app.services.sessions import _pg_load_session_bundle, _pg_session

    async def _load() -> SessionDomain:
        async with _pg_session() as db:
            record, snapshot = await _pg_load_session_bundle(db, session_id)
        return SessionDomain(record=record, snapshot=snapshot)

    return _run_async(_load())


def load_session_domain(session_id: UUID) -> SessionDomain:
    if _postgres_enabled():
        return session_domain_from_postgres(session_id)
    return session_domain_from_memory(session_id)
