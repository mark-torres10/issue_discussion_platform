from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import RepositoryConflict, RepositoryNotFound
from app.repositories._types import ConfigurationSnapshotRecord


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, snapshot: ConfigurationSnapshotRecord) -> ConfigurationSnapshotRecord:
        try:
            await self._session.execute(
                text(
                    """
                    INSERT INTO configuration_snapshots (
                        configuration_snapshot_id,
                        study_id,
                        study_wave,
                        protocol_version,
                        issue_version,
                        persona_version,
                        prompt_content_hash,
                        prompt_object_reference,
                        opening_display_text,
                        ai_speaks_first,
                        model_provider,
                        model_name,
                        model_parameters_json,
                        voice_config_json,
                        tool_manifest_hash,
                        safety_policy_version,
                        assignment_seed_reference,
                        application_version
                    ) VALUES (
                        :configuration_snapshot_id,
                        :study_id,
                        :study_wave,
                        :protocol_version,
                        :issue_version,
                        :persona_version,
                        :prompt_content_hash,
                        :prompt_object_reference,
                        :opening_display_text,
                        :ai_speaks_first,
                        :model_provider,
                        :model_name,
                        CAST(:model_parameters_json AS jsonb),
                        CAST(:voice_config_json AS jsonb),
                        :tool_manifest_hash,
                        :safety_policy_version,
                        :assignment_seed_reference,
                        :application_version
                    )
                    """
                ),
                {
                    "configuration_snapshot_id": snapshot.configuration_snapshot_id,
                    "study_id": snapshot.study_id,
                    "study_wave": snapshot.study_wave,
                    "protocol_version": snapshot.protocol_version,
                    "issue_version": snapshot.issue_version,
                    "persona_version": snapshot.persona_version,
                    "prompt_content_hash": snapshot.prompt_content_hash,
                    "prompt_object_reference": snapshot.prompt_object_reference,
                    "opening_display_text": snapshot.opening_display_text,
                    "ai_speaks_first": snapshot.ai_speaks_first,
                    "model_provider": snapshot.model_provider,
                    "model_name": snapshot.model_name,
                    "model_parameters_json": _json_dumps(snapshot.model_parameters_json),
                    "voice_config_json": _json_dumps(snapshot.voice_config_json),
                    "tool_manifest_hash": snapshot.tool_manifest_hash,
                    "safety_policy_version": snapshot.safety_policy_version,
                    "assignment_seed_reference": snapshot.assignment_seed_reference,
                    "application_version": snapshot.application_version,
                },
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise RepositoryConflict(
                "Configuration snapshot already exists",
                constraint="configuration_snapshots_pkey",
            ) from exc
        return snapshot

    async def get(self, snapshot_id: UUID) -> ConfigurationSnapshotRecord:
        result = await self._session.execute(
            text(
                "SELECT * FROM configuration_snapshots "
                "WHERE configuration_snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": snapshot_id},
        )
        row = result.mappings().first()
        if row is None:
            raise RepositoryNotFound(f"Snapshot {snapshot_id} not found")
        return ConfigurationSnapshotRecord(
            configuration_snapshot_id=row["configuration_snapshot_id"],
            study_id=row["study_id"],
            study_wave=row["study_wave"],
            protocol_version=row["protocol_version"],
            issue_version=row["issue_version"],
            persona_version=row["persona_version"],
            prompt_content_hash=row["prompt_content_hash"],
            prompt_object_reference=row["prompt_object_reference"],
            opening_display_text=row["opening_display_text"],
            ai_speaks_first=row["ai_speaks_first"],
            model_provider=row["model_provider"],
            model_name=row["model_name"],
            model_parameters_json=row["model_parameters_json"],
            voice_config_json=row["voice_config_json"],
            tool_manifest_hash=row["tool_manifest_hash"],
            safety_policy_version=row["safety_policy_version"],
            assignment_seed_reference=row["assignment_seed_reference"],
            application_version=row["application_version"],
            created_at=row["created_at"],
        )


def _json_dumps(value: dict[str, object]) -> str:
    import json

    return json.dumps(value)
