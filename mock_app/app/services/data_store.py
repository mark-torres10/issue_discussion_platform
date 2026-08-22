"""JSON-backed persistence for profiles and swipes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.config import CURRENT_USER_ID, PROFILES_JSON
from app.models.profile import Profile, SwipeDirection, SwipeRecord, VerificationKind

_store: DataStore | None = None


class DuplicateSwipeError(Exception):
    """Raised when swiping the same profile twice."""


class SelfSwipeError(Exception):
    """Raised when attempting to swipe on the current user."""


class ProfileNotFoundError(Exception):
    """Raised when a profile id does not exist."""


class DataStore:
    """Read and write profile/swipe data from a JSON file."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or PROFILES_JSON
        self._data: dict | None = None

    def load(self) -> dict:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        with self.data_path.open(encoding="utf-8") as handle:
            self._data = json.load(handle)
        return self._data

    def save(self, data: dict) -> None:
        temp_path = self.data_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        temp_path.replace(self.data_path)
        self._data = data

    def _ensure_loaded(self) -> dict:
        if self._data is None:
            return self.load()
        return self._data

    def list_profiles_for_deck(self) -> list[Profile]:
        data = self._ensure_loaded()
        swiped_ids = {swipe["profile_id"] for swipe in data.get("swipes", [])}
        profiles: list[Profile] = []
        for raw in data.get("profiles", []):
            profile_id = raw["id"]
            if profile_id == CURRENT_USER_ID:
                continue
            if profile_id in swiped_ids:
                continue
            profiles.append(Profile.model_validate(raw))
        return profiles

    def get_profile(self, profile_id: str) -> Profile | None:
        data = self._ensure_loaded()
        for raw in data.get("profiles", []):
            if raw["id"] == profile_id:
                return Profile.model_validate(raw)
        return None

    def get_current_user(self) -> Profile:
        profile = self.get_profile(CURRENT_USER_ID)
        if profile is None:
            raise KeyError(f"Current user profile not found: {CURRENT_USER_ID}")
        return profile

    def record_swipe(self, profile_id: str, direction: SwipeDirection) -> SwipeRecord:
        if profile_id == CURRENT_USER_ID:
            raise SelfSwipeError("Cannot swipe on yourself")

        if self.get_profile(profile_id) is None:
            raise ProfileNotFoundError(f"Profile not found: {profile_id}")

        data = self._ensure_loaded()
        swipes = data.setdefault("swipes", [])
        if any(swipe["profile_id"] == profile_id for swipe in swipes):
            raise DuplicateSwipeError(f"Already swiped on profile: {profile_id}")

        record = SwipeRecord(
            profile_id=profile_id,
            direction=direction,
            swiped_at=datetime.now(UTC).isoformat(),
        )
        swipes.append(record.model_dump())
        self.save(data)
        return record

    def list_swipes(self) -> list[SwipeRecord]:
        data = self._ensure_loaded()
        return [SwipeRecord.model_validate(swipe) for swipe in data.get("swipes", [])]

    def set_verification(self, kind: VerificationKind, verified: bool = True) -> Profile:
        data = self._ensure_loaded()
        for raw in data.get("profiles", []):
            if raw["id"] != CURRENT_USER_ID:
                continue
            if kind == VerificationKind.LINKEDIN:
                raw["linkedin_verified"] = verified
            elif kind == VerificationKind.TRUST_SOURCE:
                raw["trust_source_verified"] = verified
            self.save(data)
            return Profile.model_validate(raw)
        raise KeyError(f"Current user profile not found: {CURRENT_USER_ID}")


def get_data_store() -> DataStore:
    global _store
    if _store is None:
        _store = DataStore()
    return _store
