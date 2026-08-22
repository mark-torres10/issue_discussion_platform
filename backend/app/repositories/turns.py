from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FrozenModel, InteractionMode, Speaker, TurnOrigin
from app.models.enums import FrozenModel
from app.repositories import RepositoryConflict


class CanonicalTurnRecord(FrozenModel):
    turn_id: UUID
    session_id: UUID
    speaker: Speaker
    ordinal: int
    display_text: str
    source_mode: InteractionMode
    origin: TurnOrigin
    interrupted: bool = False
    recorded_at: datetime
    provider_item_id: str | None = None
    provider_response_id: str | None = None
    client_event_id: UUID | None = None
    verification_status: str = "verified"
    generated_text: str | None = None
    delivered_text: str | None = None
    content_hash: str = ""
    provider_created_at: datetime | None = None
    client_observed_at: datetime | None = None
    schema_version: int = 1


class TurnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_turn(
        self,
        *,
        turn_id: UUID,
        session_id: UUID,
        ordinal: int,
        speaker: Speaker,
        origin: TurnOrigin,
        source_mode: InteractionMode,
        display_text: str,
        content_hash: str,
        recorded_at: datetime,
        interrupted: bool = False,
        verification_status: str = "verified",
        provider_item_id: str | None = None,
        provider_response_id: str | None = None,
        client_event_id: UUID | None = None,
        client_message_id: UUID | None = None,
        generated_text: str | None = None,
        delivered_text: str | None = None,
        provider_created_at: datetime | None = None,
        client_observed_at: datetime | None = None,
        schema_version: int = 1,
    ) -> CanonicalTurnRecord:
        existing = await self._get_by_turn_id(turn_id)
        if existing is not None:
            if existing.content_hash != content_hash:
                raise RepositoryConflict(
                    "Turn id already exists with different content hash",
                    constraint="canonical_turns_pkey",
                )
            return existing

        try:
            await self._session.execute(
                text(
                    """
                    INSERT INTO canonical_turns (
                        turn_id,
                        session_id,
                        ordinal,
                        speaker,
                        origin,
                        verification_status,
                        provider_item_id,
                        provider_response_id,
                        client_event_id,
                        source_mode,
                        generated_text,
                        delivered_text,
                        display_text,
                        interrupted,
                        content_hash,
                        provider_created_at,
                        client_observed_at,
                        recorded_at,
                        schema_version
                    ) VALUES (
                        :turn_id,
                        :session_id,
                        :ordinal,
                        :speaker,
                        :origin,
                        :verification_status,
                        :provider_item_id,
                        :provider_response_id,
                        :client_event_id,
                        :source_mode,
                        :generated_text,
                        :delivered_text,
                        :display_text,
                        :interrupted,
                        :content_hash,
                        :provider_created_at,
                        :client_observed_at,
                        :recorded_at,
                        :schema_version
                    )
                    """
                ),
                {
                    "turn_id": turn_id,
                    "session_id": session_id,
                    "ordinal": ordinal,
                    "speaker": speaker.value,
                    "origin": origin.value,
                    "verification_status": verification_status,
                    "provider_item_id": provider_item_id,
                    "provider_response_id": provider_response_id,
                    "client_event_id": client_event_id,
                    "source_mode": source_mode.value,
                    "generated_text": generated_text,
                    "delivered_text": delivered_text,
                    "display_text": display_text,
                    "interrupted": interrupted,
                    "content_hash": content_hash,
                    "provider_created_at": provider_created_at,
                    "client_observed_at": client_observed_at,
                    "recorded_at": recorded_at,
                    "schema_version": schema_version,
                },
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            constraint = _constraint_name(exc)
            if constraint in {
                "canonical_turns_session_provider_item_unique",
                "canonical_turns_pkey",
            }:
                if provider_item_id is not None:
                    by_provider = await self._get_by_provider_item_id(
                        session_id, provider_item_id
                    )
                    if by_provider is not None and by_provider.turn_id != turn_id:
                        raise RepositoryConflict(
                            "Provider item id already used for this session",
                            constraint="canonical_turns_session_provider_item_unique",
                        ) from exc
                existing = await self._get_by_turn_id(turn_id)
                if existing is not None and existing.content_hash != content_hash:
                    raise RepositoryConflict(
                        "Turn id already exists with different content hash",
                        constraint="canonical_turns_pkey",
                    ) from exc
            raise RepositoryConflict(
                "Turn insert conflict",
                constraint=constraint,
            ) from exc

        inserted = await self._get_by_turn_id(turn_id)
        if inserted is None:
            raise RepositoryConflict("Turn insert failed")
        return inserted

    async def _get_by_turn_id(self, turn_id: UUID) -> CanonicalTurnRecord | None:
        result = await self._session.execute(
            text("SELECT * FROM canonical_turns WHERE turn_id = :turn_id"),
            {"turn_id": turn_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_record(row)

    async def _get_by_provider_item_id(
        self, session_id: UUID, provider_item_id: str
    ) -> CanonicalTurnRecord | None:
        result = await self._session.execute(
            text(
                """
                SELECT * FROM canonical_turns
                WHERE session_id = :session_id
                  AND provider_item_id = :provider_item_id
                """
            ),
            {"session_id": session_id, "provider_item_id": provider_item_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return _row_to_record(row)


def _row_to_record(row: object) -> CanonicalTurnRecord:
    mapping = dict(row)  # type: ignore[arg-type]
    return CanonicalTurnRecord(
        turn_id=mapping["turn_id"],
        session_id=mapping["session_id"],
        speaker=Speaker(mapping["speaker"]),
        ordinal=mapping["ordinal"],
        display_text=mapping["display_text"],
        source_mode=InteractionMode(mapping["source_mode"]),
        origin=TurnOrigin(mapping["origin"]),
        interrupted=mapping["interrupted"],
        recorded_at=mapping["recorded_at"],
        provider_item_id=mapping["provider_item_id"],
        provider_response_id=mapping["provider_response_id"],
        client_event_id=mapping["client_event_id"],
        verification_status=mapping["verification_status"],
        generated_text=mapping["generated_text"],
        delivered_text=mapping["delivered_text"],
        content_hash=mapping["content_hash"],
        provider_created_at=mapping["provider_created_at"],
        client_observed_at=mapping["client_observed_at"],
        schema_version=mapping["schema_version"],
    )


def _constraint_name(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None
    diag = getattr(orig, "diag", None)
    if diag is None:
        return None
    return getattr(diag, "constraint_name", None)
