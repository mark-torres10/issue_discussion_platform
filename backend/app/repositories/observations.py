from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observations import ObservationCreate
class ObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_observations(
        self, session_id: UUID, observations: list[ObservationCreate]
    ) -> list[ObservationCreate]:
        for observation in observations:
            await self._session.execute(
                text(
                    """
                    INSERT INTO observations (
                        observation_id,
                        session_id,
                        observation_type,
                        occurred_at,
                        connection_state,
                        client_first_audio_observed_ms,
                        client_first_transcript_observed_ms
                    ) VALUES (
                        :observation_id,
                        :session_id,
                        :observation_type,
                        :occurred_at,
                        :connection_state,
                        :client_first_audio_observed_ms,
                        :client_first_transcript_observed_ms
                    )
                    ON CONFLICT (observation_id) DO NOTHING
                    """
                ),
                {
                    "observation_id": observation.observation_id,
                    "session_id": session_id,
                    "observation_type": observation.observation_type.value,
                    "occurred_at": observation.occurred_at,
                    "connection_state": (
                        observation.connection_state.value
                        if observation.connection_state is not None
                        else None
                    ),
                    "client_first_audio_observed_ms": (
                        observation.client_first_audio_observed_ms
                    ),
                    "client_first_transcript_observed_ms": (
                        observation.client_first_transcript_observed_ms
                    ),
                },
            )
        await self._session.commit()
        return observations
