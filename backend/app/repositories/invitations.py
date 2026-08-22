"""Postgres persistence for study invitations and their bootstrap sessions."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SessionStatus
from app.models.session import SessionRecord
from app.repositories import RepositoryConflict
from app.repositories._types import (
    ConfigurationSnapshotRecord,
    InvitationRecord,
    hash_invitation_token,
    new_uuid7,
)
from app.repositories.sessions import SessionRepository
from app.repositories.snapshots import SnapshotRepository

# v1 stub study id until staff membership tables exist.
DEFAULT_STUDY_ID = UUID("018f5a20-7c3a-7000-8000-000000000099")


class InvitationRepository:
    """Creates invitations together with their configuration snapshot and session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_invitation(
        self,
        *,
        invitation_token: str,
        study_id: UUID | None = None,
        configuration_snapshot: ConfigurationSnapshotRecord,
        expires_at: datetime | None = None,
    ) -> InvitationRecord:
        """Provision a pending session and persist a hashed invitation token.

        The snapshot, session, and invitation rows are written in one flow.
        Only the token hash is stored; the raw token is never persisted.

        Raises
        ------
        RepositoryConflict
            If an invitation with the same token hash already exists.
        """
        token_hash = hash_invitation_token(invitation_token)
        study = study_id or DEFAULT_STUDY_ID
        invitation_id = new_uuid7()
        session_id = new_uuid7()
        telemetry_thread_id = new_uuid7()

        snapshot_repo = SnapshotRepository(self._session)
        await snapshot_repo.create(configuration_snapshot)

        session_record = SessionRecord(
            session_id=session_id,
            study_id=study,
            participant_capability_hash="",
            telemetry_thread_id=telemetry_thread_id,
            status=SessionStatus.pending,
            version=1,
            configuration_snapshot_id=configuration_snapshot.configuration_snapshot_id,
        )
        session_repo = SessionRepository(self._session)
        await session_repo.create(session_record)

        try:
            await self._session.execute(
                text(
                    """
                    INSERT INTO invitations (
                        invitation_id,
                        study_id,
                        session_id,
                        token_hash,
                        telemetry_thread_id,
                        expires_at
                    ) VALUES (
                        :invitation_id,
                        :study_id,
                        :session_id,
                        :token_hash,
                        :telemetry_thread_id,
                        :expires_at
                    )
                    """
                ),
                {
                    "invitation_id": invitation_id,
                    "study_id": study,
                    "session_id": session_id,
                    "token_hash": token_hash,
                    "telemetry_thread_id": telemetry_thread_id,
                    "expires_at": expires_at,
                },
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise RepositoryConflict(
                "Invitation already exists",
                constraint="invitations_token_hash_unique",
            ) from exc

        return InvitationRecord(
            invitation_id=invitation_id,
            study_id=study,
            session_id=session_id,
            token_hash=token_hash,
            telemetry_thread_id=telemetry_thread_id,
            expires_at=expires_at,
        )

    async def get_by_token_hash(self, token_hash: str) -> InvitationRecord | None:
        """Return the invitation for ``token_hash``, or ``None`` when absent."""
        result = await self._session.execute(
            text("SELECT * FROM invitations WHERE token_hash = :token_hash"),
            {"token_hash": token_hash},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return InvitationRecord(
            invitation_id=row["invitation_id"],
            study_id=row["study_id"],
            session_id=row["session_id"],
            token_hash=row["token_hash"],
            telemetry_thread_id=row["telemetry_thread_id"],
            expires_at=row["expires_at"],
            revoked_at=row["revoked_at"],
            created_at=row["created_at"],
        )

    async def token_hash_exists(self, token_hash: str) -> bool:
        """Return whether an invitation row exists for ``token_hash``."""
        result = await self._session.execute(
            text(
                "SELECT 1 FROM invitations WHERE token_hash = :token_hash LIMIT 1"
            ),
            {"token_hash": token_hash},
        )
        return result.first() is not None
