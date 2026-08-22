from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.engine import reset_engine
from app.models.enums import InteractionMode, SessionStatus, Speaker, TurnOrigin
from app.models.session import SessionRecord
from app.repositories._types import new_uuid7
from app.repositories.sessions import SessionRepository
from app.repositories.snapshots import SnapshotRepository
from app.repositories.staff_membership import StaffMembershipRepository
from app.repositories.turns import TurnRepository
from tests.test_repositories import _sample_snapshot
from tests.test_staff_auth import (
    EXPORT_PATH,
    apply_staff_membership_schema,
    make_test_jwt,
    staff_auth_headers,
    staff_jwt_env,
)

PARTICIPANT_TEXT = "Universities should protect open debate."
AI_TEXT = "That is a fair concern. How should a university decide when speech crosses the line?"


@pytest.fixture
def postgres_export_client(
    app: FastAPI,
    postgres_database_url: str,
    apply_study_schema: None,
    apply_staff_membership_schema: None,
    staff_jwt_env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("STORAGE_MODE", "postgres")
    monkeypatch.setenv("DATABASE_URL", postgres_database_url)
    from app.core.config import get_settings

    reset_engine()
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def seeded_export_session(
    db_session,
    apply_study_schema: None,
    apply_staff_membership_schema: None,
) -> dict[str, object]:
    study_id = new_uuid7()
    snapshot_id = new_uuid7()
    snapshot = _sample_snapshot(study_id=study_id, snapshot_id=snapshot_id)
    snapshot_repo = SnapshotRepository(db_session)
    await snapshot_repo.create(snapshot)

    session_id = new_uuid7()
    telemetry_thread_id = new_uuid7()
    session_repo = SessionRepository(db_session)
    await session_repo.create(
        SessionRecord(
            session_id=session_id,
            study_id=study_id,
            participant_capability_hash="export-capability-hash",
            telemetry_thread_id=telemetry_thread_id,
            status=SessionStatus.active,
            version=2,
            configuration_snapshot_id=snapshot_id,
        )
    )

    turn_repo = TurnRepository(db_session)
    now = datetime.now(UTC)
    await turn_repo.insert_turn(
        turn_id=new_uuid7(),
        session_id=session_id,
        ordinal=0,
        speaker=Speaker.participant,
        origin=TurnOrigin.study_api_text,
        source_mode=InteractionMode.text,
        display_text=PARTICIPANT_TEXT,
        content_hash="export-hash-participant",
        recorded_at=now,
    )
    await turn_repo.insert_turn(
        turn_id=new_uuid7(),
        session_id=session_id,
        ordinal=1,
        speaker=Speaker.ai,
        origin=TurnOrigin.study_api_text,
        source_mode=InteractionMode.text,
        display_text=AI_TEXT,
        content_hash="export-hash-ai",
        recorded_at=now,
    )

    return {
        "session_id": session_id,
        "study_id": study_id,
    }


class TestSessionExport:
    async def test_export_contains_canonical_turns(
        self,
        postgres_export_client: TestClient,
        seeded_export_session: dict[str, object],
        db_session,
    ) -> None:
        session_id = seeded_export_session["session_id"]
        study_id = seeded_export_session["study_id"]
        staff_user_id = f"researcher-{new_uuid7()}"

        membership_repo = StaffMembershipRepository(db_session)
        await membership_repo.upsert(
            study_id=study_id,
            user_id=staff_user_id,
            role="researcher",
        )

        token = make_test_jwt(sub=staff_user_id)
        response = postgres_export_client.get(
            EXPORT_PATH.format(session_id=session_id),
            headers=staff_auth_headers(token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == str(session_id)
        assert body["telemetry_thread_id"]
        assert len(body["turns"]) == 2
        display_texts = [turn["display_text"] for turn in body["turns"]]
        assert PARTICIPANT_TEXT in display_texts
        assert AI_TEXT in display_texts
        assert body["turns"] == sorted(body["turns"], key=lambda turn: turn["ordinal"])

    async def test_export_denied_without_membership(
        self,
        postgres_export_client: TestClient,
        seeded_export_session: dict[str, object],
    ) -> None:
        session_id = seeded_export_session["session_id"]
        token = make_test_jwt(sub=f"unauthorized-{new_uuid7()}")

        response = postgres_export_client.get(
            EXPORT_PATH.format(session_id=session_id),
            headers=staff_auth_headers(token),
        )

        assert response.status_code == 403
        assert response.json()["error_code"] == "staff_forbidden"


class TestExportManifest:
    async def test_manifest_version_present(
        self,
        postgres_export_client: TestClient,
        seeded_export_session: dict[str, object],
        db_session,
    ) -> None:
        session_id = seeded_export_session["session_id"]
        study_id = seeded_export_session["study_id"]
        staff_user_id = f"study-admin-{new_uuid7()}"

        membership_repo = StaffMembershipRepository(db_session)
        await membership_repo.upsert(
            study_id=study_id,
            user_id=staff_user_id,
            role="study_admin",
        )

        token = make_test_jwt(sub=staff_user_id)
        response = postgres_export_client.get(
            EXPORT_PATH.format(session_id=session_id),
            headers=staff_auth_headers(token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["manifest_version"] == "1.0.0"
        assert body["ai_text_field"] == "display_text"
        assert body["configuration_snapshot_id"]
        assert body["status"] in {
            "pending",
            "active",
            "paused",
            "completed",
            "expired",
        }

    async def test_export_reads_only_committed_turns(
        self,
        postgres_export_client: TestClient,
        seeded_export_session: dict[str, object],
        db_session,
    ) -> None:
        session_id = seeded_export_session["session_id"]
        study_id = seeded_export_session["study_id"]
        staff_user_id = f"researcher-{new_uuid7()}"

        membership_repo = StaffMembershipRepository(db_session)
        await membership_repo.upsert(
            study_id=study_id,
            user_id=staff_user_id,
            role="researcher",
        )
        turn_repo = TurnRepository(db_session)
        await turn_repo.insert_turn(
            turn_id=new_uuid7(),
            session_id=session_id,
            ordinal=99,
            speaker=Speaker.ai,
            origin=TurnOrigin.study_api_text,
            source_mode=InteractionMode.text,
            display_text="Committed export turn",
            content_hash="export-hash-committed",
            recorded_at=datetime.now(UTC),
        )
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM canonical_turns WHERE session_id = :session_id"),
            {"session_id": session_id},
        )
        committed_count = int(result.scalar_one())

        token = make_test_jwt(sub=staff_user_id)
        response = postgres_export_client.get(
            EXPORT_PATH.format(session_id=session_id),
            headers=staff_auth_headers(token),
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["turns"]) == committed_count
        assert all(
            turn["display_text"] != "Invented uncommitted turn"
            for turn in body["turns"]
        )

    async def test_audit_event_has_no_transcript_text(
        self,
        postgres_export_client: TestClient,
        seeded_export_session: dict[str, object],
        db_session,
    ) -> None:
        session_id = seeded_export_session["session_id"]
        study_id = seeded_export_session["study_id"]
        staff_user_id = f"researcher-{new_uuid7()}"

        membership_repo = StaffMembershipRepository(db_session)
        await membership_repo.upsert(
            study_id=study_id,
            user_id=staff_user_id,
            role="researcher",
        )

        token = make_test_jwt(sub=staff_user_id)
        response = postgres_export_client.get(
            EXPORT_PATH.format(session_id=session_id),
            headers=staff_auth_headers(token),
        )
        assert response.status_code == 200

        result = await db_session.execute(
            text(
                """
                SELECT action, metadata_json
                FROM audit_events
                WHERE object_id = :object_id
                  AND action = 'transcript_export'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"object_id": str(session_id)},
        )
        row = result.mappings().first()
        assert row is not None
        serialized = str(row["metadata_json"])
        for turn in response.json()["turns"]:
            assert turn["display_text"] not in serialized
