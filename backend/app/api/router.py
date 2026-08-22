from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.internal.realtime_items import router as internal_realtime_router
from app.api.messages import router as messages_router
from app.api.observations import router as observations_router
from app.api.participant_access import router as participant_access_router
from app.api.participant_session import router as participant_session_router
from app.api.realtime import router as realtime_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(participant_access_router)
api_router.include_router(participant_session_router)
api_router.include_router(messages_router)
api_router.include_router(observations_router)
api_router.include_router(realtime_router)
api_router.include_router(internal_realtime_router)
