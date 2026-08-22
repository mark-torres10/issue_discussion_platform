"""Swipe HTTP routes."""

from fastapi import APIRouter, HTTPException

from app.models.profile import SwipeRecord, SwipeRequest
from app.services.data_store import (
    DuplicateSwipeError,
    ProfileNotFoundError,
    SelfSwipeError,
    get_data_store,
)

router = APIRouter(tags=["swipes"])


@router.post("/swipes", status_code=201)
def create_swipe(body: SwipeRequest) -> SwipeRecord:
    store = get_data_store()
    try:
        return store.record_swipe(body.profile_id, body.direction)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Profile not found") from exc
    except SelfSwipeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DuplicateSwipeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/swipes")
def list_swipes() -> dict:
    store = get_data_store()
    return {"swipes": store.list_swipes()}
