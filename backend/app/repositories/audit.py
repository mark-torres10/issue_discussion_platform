from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories._types import AuditEventRecord, new_uuid7


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append_event(self, event: AuditEventRecord) -> AuditEventRecord:
        audit_event_id = event.audit_event_id or new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO audit_events (
                    audit_event_id,
                    study_id,
                    actor_type,
                    actor_id,
                    action,
                    object_type,
                    object_id,
                    authorization_result,
                    request_id,
                    object_version,
                    metadata_json
                ) VALUES (
                    :audit_event_id,
                    :study_id,
                    :actor_type,
                    :actor_id,
                    :action,
                    :object_type,
                    :object_id,
                    :authorization_result,
                    :request_id,
                    :object_version,
                    CAST(:metadata_json AS jsonb)
                )
                """
            ),
            {
                "audit_event_id": audit_event_id,
                "study_id": event.study_id,
                "actor_type": event.actor_type,
                "actor_id": event.actor_id,
                "action": event.action,
                "object_type": event.object_type,
                "object_id": event.object_id,
                "authorization_result": event.authorization_result,
                "request_id": event.request_id,
                "object_version": event.object_version,
                "metadata_json": _json_dumps(event.metadata_json),
            },
        )
        await self._session.commit()
        return event.model_copy(update={"audit_event_id": audit_event_id})


def _json_dumps(value: dict[str, object]) -> str:
    import json

    return json.dumps(value)
