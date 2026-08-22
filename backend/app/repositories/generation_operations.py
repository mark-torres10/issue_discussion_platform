"""Postgres persistence for text-generation idempotency records."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import GenerationOperationStatus
from app.models.generation import GenerationOperation
from app.repositories._types import new_uuid7


class GenerationOperationRepository:
    """Tracks generation operations keyed by session-scoped idempotency tuples."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _row_to_record(row: Any) -> GenerationOperation:
        return GenerationOperation(
            operation_id=row["operation_id"],
            session_id=row["session_id"],
            idempotency_scope=row["idempotency_scope"],
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            status=GenerationOperationStatus(row["status"]),
            participant_turn_id=row["participant_turn_id"],
            ai_turn_id=row["ai_turn_id"],
            model_name=row["model_name"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            response_body=row["response_body"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def get_by_idempotency(
        self,
        session_id: UUID,
        *,
        scope: str,
        key: str,
    ) -> GenerationOperation | None:
        """Return the operation for the idempotency tuple, if one exists."""
        result = await self._session.execute(
            text(
                """
                SELECT *
                FROM generation_operations
                WHERE session_id = :session_id
                  AND idempotency_scope = :scope
                  AND idempotency_key = :key
                """
            ),
            {"session_id": session_id, "scope": scope, "key": key},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return self._row_to_record(row)

    async def create_accepted(
        self,
        *,
        session_id: UUID,
        scope: str,
        key: str,
        request_hash: str,
        model_name: str,
        participant_turn_id: UUID,
        operation_id: UUID | None = None,
    ) -> GenerationOperation:
        """Insert a new operation in the ``accepted`` state."""
        now = datetime.now(UTC)
        op_id = operation_id or new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO generation_operations (
                    operation_id, session_id, idempotency_scope, idempotency_key,
                    request_hash, status, participant_turn_id, model_name,
                    created_at, updated_at
                ) VALUES (
                    :operation_id, :session_id, :scope, :key,
                    :request_hash, :status, :participant_turn_id, :model_name,
                    :created_at, :updated_at
                )
                """
            ),
            {
                "operation_id": op_id,
                "session_id": session_id,
                "scope": scope,
                "key": key,
                "request_hash": request_hash,
                "status": GenerationOperationStatus.accepted.value,
                "participant_turn_id": participant_turn_id,
                "model_name": model_name,
                "created_at": now,
                "updated_at": now,
            },
        )
        return GenerationOperation(
            operation_id=op_id,
            session_id=session_id,
            idempotency_scope=scope,
            idempotency_key=key,
            request_hash=request_hash,
            status=GenerationOperationStatus.accepted,
            participant_turn_id=participant_turn_id,
            model_name=model_name,
            created_at=now,
            updated_at=now,
        )

    async def update_status(
        self,
        operation_id: UUID,
        *,
        status: GenerationOperationStatus,
        ai_turn_id: UUID | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        """Update operation status and optional result fields."""
        now = datetime.now(UTC)
        await self._session.execute(
            text(
                """
                UPDATE generation_operations
                SET status = :status,
                    ai_turn_id = COALESCE(:ai_turn_id, ai_turn_id),
                    error_code = :error_code,
                    error_message = :error_message,
                    response_body = :response_body,
                    updated_at = :updated_at
                WHERE operation_id = :operation_id
                """
            ),
            {
                "operation_id": operation_id,
                "status": status.value,
                "ai_turn_id": ai_turn_id,
                "error_code": error_code,
                "error_message": error_message,
                "response_body": response_body,
                "updated_at": now,
            },
        )
