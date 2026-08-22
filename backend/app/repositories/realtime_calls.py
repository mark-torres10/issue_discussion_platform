"""Postgres persistence for OpenAI realtime call bookkeeping."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FrozenModel


class RealtimeCallRecord(FrozenModel):
    """Immutable row describing one OpenAI realtime call for a session."""


class RealtimeCallRepository:
    """Tracks realtime call setup, lookup, and invalidation per session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: RealtimeCallRecord) -> RealtimeCallRecord:
        """Insert a realtime call row and commit the transaction."""
        await self._session.execute(
            text(
                """
                INSERT INTO realtime_calls (
                    realtime_call_id,
                    session_id,
                    openai_call_id,
                    capability_id,
                    status,
                    expires_at,
                    invalidated_at,
                    control_handoff_enqueued_at
                ) VALUES (
                    :realtime_call_id,
                    :session_id,
                    :openai_call_id,
                    :capability_id,
                    :status,
                    :expires_at,
                    :invalidated_at,
                    :control_handoff_enqueued_at
                )
                """
            ),
            {
                "realtime_call_id": record.realtime_call_id,
                "session_id": record.session_id,
                "openai_call_id": record.openai_call_id,
                "capability_id": record.capability_id,
                "status": record.status,
                "expires_at": record.expires_at,
                "invalidated_at": record.invalidated_at,
                "control_handoff_enqueued_at": record.control_handoff_enqueued_at,
            },
        )
        await self._session.commit()
        return record

    async def invalidate_active_for_session(
        self, session_id: UUID, *, invalidated_at: datetime
    ) -> None:
        """Mark all active realtime calls for ``session_id`` as invalidated."""
        await self._session.execute(
            text(
                """
                UPDATE realtime_calls
                SET status = 'invalidated', invalidated_at = :invalidated_at
                WHERE session_id = :session_id AND status = 'active'
                """
            ),
            {
                "session_id": session_id,
                "invalidated_at": invalidated_at,
            },
        )
        await self._session.commit()

    async def get_by_openai_call_id(self, openai_call_id: str) -> RealtimeCallRecord | None:
        """Return the realtime call row for ``openai_call_id``, if present."""
        result = await self._session.execute(
            text("SELECT * FROM realtime_calls WHERE openai_call_id = :openai_call_id"),
            {"openai_call_id": openai_call_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_record(row)

    async def count_successful_setups(self, session_id: UUID) -> int:
        """Return how many realtime call rows exist for ``session_id``."""
        result = await self._session.execute(
            text(
                """
                SELECT COUNT(*) AS count
                FROM realtime_calls
                WHERE session_id = :session_id
                """
            ),
            {"session_id": session_id},
        )
        return int(result.scalar_one())


def _row_to_record(row: object) -> RealtimeCallRecord:
    mapping = dict(row)  # type: ignore[arg-type]
    return RealtimeCallRecord(
        realtime_call_id=mapping["realtime_call_id"],
        session_id=mapping["session_id"],
        openai_call_id=mapping["openai_call_id"],
        capability_id=mapping["capability_id"],
        status=mapping["status"],
        expires_at=mapping["expires_at"],
        invalidated_at=mapping["invalidated_at"],
        control_handoff_enqueued_at=mapping["control_handoff_enqueued_at"],
        created_at=mapping.get("created_at"),
    )
