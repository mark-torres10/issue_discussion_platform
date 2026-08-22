"""Staff export of committed session transcripts."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.staff_auth import require_export_role
from app.models.enums import InteractionMode, Speaker
from app.models.export import (
    AI_TEXT_EXPORT_FIELD,
    EXPORT_MANIFEST_VERSION,
    ExportTurn,
    SessionExportManifest,
)
from app.repositories import RepositoryNotFound
from app.repositories._types import AuditEventRecord, new_uuid7
from app.repositories.audit import AuditRepository
from app.repositories.sessions import SessionRepository
from app.repositories.staff_membership import StaffMembershipRepository
from app.services.sessions import StudyApiError


async def _list_committed_turns(
    db: AsyncSession, session_id: UUID
) -> list[ExportTurn]:
    result = await db.execute(
        text(
            """
            SELECT turn_id, speaker, ordinal, display_text,
                   source_mode, interrupted, recorded_at
            FROM canonical_turns
            WHERE session_id = :session_id
            ORDER BY ordinal ASC
            """
        ),
        {"session_id": session_id},
    )
    turns: list[ExportTurn] = []
    for row in result.mappings():
        turns.append(
            ExportTurn(
                turn_id=row["turn_id"],
                speaker=Speaker(row["speaker"]),
                ordinal=row["ordinal"],
                display_text=row["display_text"],
                source_mode=InteractionMode(row["source_mode"]),
                interrupted=row["interrupted"],
                recorded_at=row["recorded_at"],
            )
        )
    return turns


async def export_session(
    session_id: UUID,
    staff_user_id: str,
    *,
    request_id: str | None = None,
) -> SessionExportManifest:
    """Build a staff-facing export manifest for one session's committed turns.

    Verifies study membership and export role before reading canonical turns.
    Appends an audit event describing the export.

    Raises
    ------
    StudyApiError
        If the session is missing or the staff user lacks export permission.
    """
    from app.db.session import get_db_session

    async with get_db_session() as db:
        session_repo = SessionRepository(db)
        try:
            record = await session_repo.get(session_id)
        except RepositoryNotFound as exc:
            raise StudyApiError(
                status_code=404,
                error_code="session_not_found",
                message="Session not found",
            ) from exc

        membership_repo = StaffMembershipRepository(db)
        membership = await membership_repo.get(record.study_id, staff_user_id)
        if membership is None:
            raise StudyApiError(
                status_code=403,
                error_code="staff_forbidden",
                message="Staff membership is required for this study",
            )
        require_export_role(membership.role)

        turns = await _list_committed_turns(db, session_id)

        audit_repo = AuditRepository(db)
        await audit_repo.append_event(
            AuditEventRecord(
                audit_event_id=new_uuid7(),
                study_id=record.study_id,
                actor_type="staff",
                actor_id=staff_user_id,
                action="transcript_export",
                object_type="session",
                object_id=str(session_id),
                authorization_result="allowed",
                request_id=request_id,
                object_version=record.version,
                metadata_json={
                    "turn_count": len(turns),
                    "manifest_version": EXPORT_MANIFEST_VERSION,
                },
            )
        )

        return SessionExportManifest(
            manifest_version=EXPORT_MANIFEST_VERSION,
            ai_text_field=AI_TEXT_EXPORT_FIELD,
            session_id=record.session_id,
            study_id=record.study_id,
            status=record.status,
            configuration_snapshot_id=record.configuration_snapshot_id,
            telemetry_thread_id=record.telemetry_thread_id,
            consent_version=record.consent_version,
            consented_at=record.consented_at,
            consent_profile=record.consent_profile,
            consent_withdrawn_at=record.consent_withdrawn_at,
            turns=turns,
        )
