from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FrozenModel
from app.repositories._types import new_uuid7

StaffRole = str


class StaffMembershipRecord(FrozenModel):
    membership_id: UUID
    study_id: UUID
    user_id: str
    role: StaffRole


class StaffMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, study_id: UUID, user_id: str) -> StaffMembershipRecord | None:
        result = await self._session.execute(
            text(
                """
                SELECT membership_id, study_id, user_id, role
                FROM staff_membership
                WHERE study_id = :study_id
                  AND user_id = :user_id
                """
            ),
            {"study_id": study_id, "user_id": user_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return StaffMembershipRecord(
            membership_id=row["membership_id"],
            study_id=row["study_id"],
            user_id=row["user_id"],
            role=row["role"],
        )

    async def upsert(
        self,
        *,
        study_id: UUID,
        user_id: str,
        role: StaffRole,
    ) -> StaffMembershipRecord:
        membership_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO staff_membership (
                    membership_id,
                    study_id,
                    user_id,
                    role
                ) VALUES (
                    :membership_id,
                    :study_id,
                    :user_id,
                    :role
                )
                ON CONFLICT (study_id, user_id) DO UPDATE
                SET role = EXCLUDED.role
                """
            ),
            {
                "membership_id": membership_id,
                "study_id": study_id,
                "user_id": user_id,
                "role": role,
            },
        )
        await self._session.commit()
        membership = await self.get(study_id, user_id)
        if membership is None:
            raise RuntimeError("Failed to upsert staff membership")
        return membership
