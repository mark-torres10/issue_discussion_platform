from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracing import TraceExportKind, TraceKind, TraceRunRecord
from app.repositories._types import new_uuid7


class TraceRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_canonical_turn(
        self, canonical_turn_id: UUID, *, export_kind: TraceExportKind
    ) -> TraceRunRecord | None:
        result = await self._session.execute(
            text(
                """
                SELECT trace_run_id, session_id, export_kind, langsmith_root_run_id,
                       canonical_turn_id, trace_kind, created_at
                FROM trace_runs
                WHERE canonical_turn_id = :canonical_turn_id
                  AND export_kind = :export_kind
                """
            ),
            {
                "canonical_turn_id": canonical_turn_id,
                "export_kind": export_kind.value,
            },
        )
        row = result.mappings().first()
        if row is None:
            return None
        return TraceRunRecord(
            trace_run_id=row["trace_run_id"],
            session_id=row["session_id"],
            export_kind=TraceExportKind(row["export_kind"]),
            langsmith_root_run_id=row["langsmith_root_run_id"],
            canonical_turn_id=row["canonical_turn_id"],
            trace_kind=(
                TraceKind(row["trace_kind"]) if row["trace_kind"] is not None else None
            ),
            created_at=row["created_at"],
        )

    async def upsert(
        self,
        *,
        session_id: UUID,
        export_kind: TraceExportKind,
        langsmith_root_run_id: UUID,
        canonical_turn_id: UUID | None = None,
        trace_kind: TraceKind | None = None,
    ) -> TraceRunRecord:
        now = datetime.now(UTC)
        trace_run_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO trace_runs (
                    trace_run_id, session_id, export_kind, langsmith_root_run_id,
                    canonical_turn_id, trace_kind, created_at
                ) VALUES (
                    :trace_run_id, :session_id, :export_kind, :langsmith_root_run_id,
                    :canonical_turn_id, :trace_kind, :created_at
                )
                ON CONFLICT (canonical_turn_id, export_kind)
                WHERE canonical_turn_id IS NOT NULL
                DO UPDATE SET langsmith_root_run_id = EXCLUDED.langsmith_root_run_id
                """
            ),
            {
                "trace_run_id": trace_run_id,
                "session_id": session_id,
                "export_kind": export_kind.value,
                "langsmith_root_run_id": langsmith_root_run_id,
                "canonical_turn_id": canonical_turn_id,
                "trace_kind": trace_kind.value if trace_kind is not None else None,
                "created_at": now,
            },
        )
        if canonical_turn_id is not None:
            existing = await self.get_by_canonical_turn(
                canonical_turn_id, export_kind=export_kind
            )
            if existing is not None:
                return existing
        return TraceRunRecord(
            trace_run_id=trace_run_id,
            session_id=session_id,
            export_kind=export_kind,
            langsmith_root_run_id=langsmith_root_run_id,
            canonical_turn_id=canonical_turn_id,
            trace_kind=trace_kind,
            created_at=now,
        )


_memory_trace_runs: dict[tuple[UUID, TraceExportKind], TraceRunRecord] = {}


def reset_memory_trace_runs() -> None:
    _memory_trace_runs.clear()


def memory_get_trace_run(
    canonical_turn_id: UUID, *, export_kind: TraceExportKind
) -> TraceRunRecord | None:
    return _memory_trace_runs.get((canonical_turn_id, export_kind))


def memory_upsert_trace_run(
    *,
    session_id: UUID,
    export_kind: TraceExportKind,
    langsmith_root_run_id: UUID,
    canonical_turn_id: UUID | None = None,
    trace_kind: TraceKind | None = None,
) -> TraceRunRecord:
    now = datetime.now(UTC)
    if canonical_turn_id is not None:
        key = (canonical_turn_id, export_kind)
        existing = _memory_trace_runs.get(key)
        if existing is not None:
            return existing
        record = TraceRunRecord(
            trace_run_id=new_uuid7(),
            session_id=session_id,
            export_kind=export_kind,
            langsmith_root_run_id=langsmith_root_run_id,
            canonical_turn_id=canonical_turn_id,
            trace_kind=trace_kind,
            created_at=now,
        )
        _memory_trace_runs[key] = record
        return record
    record = TraceRunRecord(
        trace_run_id=new_uuid7(),
        session_id=session_id,
        export_kind=export_kind,
        langsmith_root_run_id=langsmith_root_run_id,
        canonical_turn_id=canonical_turn_id,
        trace_kind=trace_kind,
        created_at=now,
    )
    return record
