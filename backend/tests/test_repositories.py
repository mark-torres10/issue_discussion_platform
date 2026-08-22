from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import text

from app.models.enums import InteractionMode, SessionStatus, Speaker, TurnOrigin
from app.models.session import SessionRecord
from app.repositories import RepositoryConflict
from app.repositories._types import (
    ConfigurationSnapshotRecord,
    hash_invitation_token,
    new_uuid7,
)
from app.repositories.invitations import InvitationRepository
from app.repositories.sessions import SessionRepository
from app.repositories.snapshots import SnapshotRepository
from app.repositories.turns import TurnRepository


def _sample_snapshot(*, study_id: UUID, snapshot_id: UUID | None = None) -> ConfigurationSnapshotRecord:
    return ConfigurationSnapshotRecord(
        configuration_snapshot_id=snapshot_id or new_uuid7(),
        study_id=study_id,
        study_wave="pilot-2026-fall",
        protocol_version="v1",
        issue_version="demo-campus-speech-001",
        persona_version="v1",
        prompt_content_hash="abc123",
        prompt_object_reference="prompts/demo-v1.json",
        opening_display_text="Hello from the study.",
        ai_speaks_first=True,
        model_provider="openai",
        model_name="gpt-4.1-mini",
        tool_manifest_hash="tools-v1",
        safety_policy_version="safety-v1",
        assignment_seed_reference="seed-001",
        application_version="test",
    )


class TestInvitationRepository:
    async def test_stores_hash_not_raw_token(self, db_session) -> None:
        raw_token = f"test-invitation-token-{new_uuid7()}"
        study_id = new_uuid7()
        snapshot = _sample_snapshot(study_id=study_id)
        repo = InvitationRepository(db_session)

        invitation = await repo.create_invitation(
            invitation_token=raw_token,
            study_id=study_id,
            configuration_snapshot=snapshot,
        )

        assert invitation.token_hash == hash_invitation_token(raw_token)
        assert invitation.token_hash != raw_token

        result = await db_session.execute(
            text("SELECT token_hash FROM invitations WHERE invitation_id = :id"),
            {"id": invitation.invitation_id},
        )
        stored_hash = result.scalar_one()
        assert stored_hash == hash_invitation_token(raw_token)
        assert stored_hash != raw_token


class TestTurnRepository:
    async def test_duplicate_provider_item_id_rejected(self, db_session) -> None:
        study_id = new_uuid7()
        snapshot = _sample_snapshot(study_id=study_id)
        invitation_repo = InvitationRepository(db_session)
        invitation = await invitation_repo.create_invitation(
            invitation_token=f"duplicate-provider-item-token-{new_uuid7()}",
            study_id=study_id,
            configuration_snapshot=snapshot,
        )
        turn_repo = TurnRepository(db_session)
        now = datetime.now(UTC)
        provider_item_id = "provider-item-123"

        await turn_repo.insert_turn(
            turn_id=new_uuid7(),
            session_id=invitation.session_id,
            ordinal=0,
            speaker=Speaker.ai,
            origin=TurnOrigin.provider_realtime,
            source_mode=InteractionMode.voice,
            display_text="First turn",
            content_hash="hash-a",
            recorded_at=now,
            provider_item_id=provider_item_id,
        )

        with pytest.raises(RepositoryConflict):
            await turn_repo.insert_turn(
                turn_id=new_uuid7(),
                session_id=invitation.session_id,
                ordinal=1,
                speaker=Speaker.ai,
                origin=TurnOrigin.provider_realtime,
                source_mode=InteractionMode.voice,
                display_text="Conflicting turn",
                content_hash="hash-b",
                recorded_at=now,
                provider_item_id=provider_item_id,
            )


class TestSessionRepository:
    async def test_version_increment(self, db_session) -> None:
        study_id = new_uuid7()
        snapshot_id = new_uuid7()
        snapshot = _sample_snapshot(study_id=study_id, snapshot_id=snapshot_id)
        snapshot_repo = SnapshotRepository(db_session)
        await snapshot_repo.create(snapshot)

        session_id = new_uuid7()
        telemetry_thread_id = new_uuid7()
        record = SessionRecord(
            session_id=session_id,
            study_id=study_id,
            participant_capability_hash="",
            telemetry_thread_id=telemetry_thread_id,
            status=SessionStatus.pending,
            version=1,
            configuration_snapshot_id=snapshot_id,
        )
        repo = SessionRepository(db_session)
        await repo.create(record)

        updated = await repo.increment_version(session_id, expected_version=1)
        assert updated.version == 2

        with pytest.raises(RepositoryConflict):
            await repo.increment_version(session_id, expected_version=1)


class TestSnapshotRepository:
    async def test_snapshot_immutable(self, db_session) -> None:
        study_id = new_uuid7()
        snapshot = _sample_snapshot(study_id=study_id)
        repo = SnapshotRepository(db_session)

        assert not hasattr(repo, "update")

        created = await repo.create(snapshot)
        fetched = await repo.get(created.configuration_snapshot_id)
        assert fetched.prompt_content_hash == created.prompt_content_hash

        with pytest.raises(RepositoryConflict):
            await repo.create(snapshot)
