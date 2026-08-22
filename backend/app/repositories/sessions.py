"""Postgres persistence for participant session records."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import SessionRecord
from app.repositories import RepositoryConflict, RepositoryNotFound
from app.repositories._types import new_uuid7


class SessionRepository:
    """Reads and writes ``sessions`` rows with optimistic versioning."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: SessionRecord) -> SessionRecord:
        """Insert a new session and commit the transaction."""
        await self._session.execute(
            text(
                """
                INSERT INTO sessions (
                    session_id,
                    study_id,
                    participant_capability_hash,
                    telemetry_thread_id,
                    status,
                    version,
                    writer_lease_id,
                    writer_lease_expires_at,
                    configuration_snapshot_id,
                    consent_version,
                    consented_at,
                    consent_profile,
                    consent_withdrawn_at,
                    started_at,
                    completed_at,
                    completion_reason
                ) VALUES (
                    :session_id,
                    :study_id,
                    :participant_capability_hash,
                    :telemetry_thread_id,
                    :status,
                    :version,
                    :writer_lease_id,
                    :writer_lease_expires_at,
                    :configuration_snapshot_id,
                    :consent_version,
                    :consented_at,
                    :consent_profile,
                    :consent_withdrawn_at,
                    :started_at,
                    :completed_at,
                    :completion_reason
                )
                """
            ),
            {
                "session_id": record.session_id,
                "study_id": record.study_id,
                "participant_capability_hash": record.participant_capability_hash,
                "telemetry_thread_id": record.telemetry_thread_id,
                "status": record.status.value,
                "version": record.version,
                "writer_lease_id": record.writer_lease_id,
                "writer_lease_expires_at": record.writer_lease_expires_at,
                "configuration_snapshot_id": record.configuration_snapshot_id,
                "consent_version": record.consent_version,
                "consented_at": record.consented_at,
                "consent_profile": record.consent_profile,
                "consent_withdrawn_at": record.consent_withdrawn_at,
                "started_at": record.started_at,
                "completed_at": record.completed_at,
                "completion_reason": record.completion_reason,
            },
        )
        await self._session.commit()
        return record

    async def get(self, session_id: UUID) -> SessionRecord:
        """Return the session for ``session_id``.

        Raises
        ------
        RepositoryNotFound
            If no session exists with the given id.
        """
        result = await self._session.execute(
            text("SELECT * FROM sessions WHERE session_id = :session_id"),
            {"session_id": session_id},
        )
        row = result.mappings().first()
        if row is None:
            raise RepositoryNotFound(f"Session {session_id} not found")
        return self._row_to_record(row)

    async def increment_version(
        self, session_id: UUID, *, expected_version: int
    ) -> SessionRecord:
        """Bump the session version when ``expected_version`` matches.

        Raises
        ------
        RepositoryNotFound
            If the session does not exist.
        RepositoryConflict
            If another writer already advanced the version.
        """
        result = await self._session.execute(
            text(
                """
                UPDATE sessions
                SET version = version + 1,
                    updated_at = now()
                WHERE session_id = :session_id
                  AND version = :expected_version
                RETURNING *
                """
            ),
            {"session_id": session_id, "expected_version": expected_version},
        )
        row = result.mappings().first()
        if row is None:
            current = await self._session.execute(
                text("SELECT version FROM sessions WHERE session_id = :session_id"),
                {"session_id": session_id},
            )
            existing = current.mappings().first()
            if existing is None:
                raise RepositoryNotFound(f"Session {session_id} not found")
            raise RepositoryConflict(
                "Session version conflict",
                constraint="sessions_version",
            )
        await self._session.commit()
        return self._row_to_record(row)

    async def complete_session(
        self,
        session_id: UUID,
        *,
        expected_version: int,
        completion_reason: str,
        completed_at: datetime,
        recovery_observations: list[object],
    ) -> SessionRecord:
        """Mark a session completed and release any writer lease.

        ``recovery_observations`` is reserved for a later completion
        transaction that will persist recovery telemetry alongside status.

        Raises
        ------
        RepositoryConflict
            If ``expected_version`` does not match the stored row.
        """
        _ = recovery_observations
        result = await self._session.execute(
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
                RETURNING *
                """
            ),
            {
                "session_id": session_id,
                "expected_version": expected_version,
                "completion_reason": completion_reason,
                "completed_at": completed_at,
            },
        )
        row = result.mappings().first()
        if row is None:
            raise RepositoryConflict(
                "Session version conflict during completion",
                constraint="sessions_version",
            )
        await self._session.commit()
        return self._row_to_record(row)

    @staticmethod
    def _row_to_record(row: object) -> SessionRecord:
        from app.models.enums import SessionStatus

        mapping = dict(row)  # type: ignore[arg-type]
        return SessionRecord(
            session_id=mapping["session_id"],
            study_id=mapping["study_id"],
            participant_capability_hash=mapping["participant_capability_hash"],
            telemetry_thread_id=mapping["telemetry_thread_id"],
            status=SessionStatus(mapping["status"]),
            version=mapping["version"],
            writer_lease_id=mapping["writer_lease_id"],
            writer_lease_expires_at=mapping["writer_lease_expires_at"],
            configuration_snapshot_id=mapping["configuration_snapshot_id"],
            consent_version=mapping["consent_version"],
            consented_at=mapping["consented_at"],
            consent_profile=mapping["consent_profile"],
            consent_withdrawn_at=mapping["consent_withdrawn_at"],
            started_at=mapping["started_at"],
            completed_at=mapping["completed_at"],
            completion_reason=mapping["completion_reason"],
        )
