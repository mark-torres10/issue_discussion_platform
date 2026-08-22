"""Profile HTTP routes."""

from fastapi import APIRouter, HTTPException

from app.models.profile import Profile
from app.services.data_store import get_data_store

router = APIRouter(tags=["profiles"])


def profile_to_response(profile: Profile) -> dict:
    payload = profile.model_dump()
    payload["photo_urls"] = [f"/mock-photos/{filename}" for filename in profile.photos]
    return payload


@router.get("/me")
def get_me() -> dict:
    store = get_data_store()
    try:
        profile = store.get_current_user()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Profile not found") from exc
    return profile_to_response(profile)


@router.get("/profiles")
def list_profiles() -> dict:
    store = get_data_store()
    profiles = store.list_profiles_for_deck()
    return {"profiles": [profile_to_response(profile) for profile in profiles]}


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: str) -> dict:
    store = get_data_store()
    profile = store.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile_to_response(profile)
