"""Profile and swipe data models."""

from enum import Enum

from pydantic import BaseModel


class WorkEntry(BaseModel):
    company: str
    title: str
    start_year: int
    end_year: int | None = None


class EducationEntry(BaseModel):
    school: str
    degree: str
    year: int


class Profile(BaseModel):
    id: str
    name: str
    bio: str
    photos: list[str]
    work_history: list[WorkEntry]
    education_background: list[EducationEntry]
    linkedin_verified: bool = False
    trust_source_verified: bool = False


class SwipeDirection(str, Enum):
    LIKE = "like"
    PASS = "pass"


class SwipeRequest(BaseModel):
    profile_id: str
    direction: SwipeDirection


class SwipeRecord(BaseModel):
    profile_id: str
    direction: SwipeDirection
    swiped_at: str


class VerificationKind(str, Enum):
    LINKEDIN = "linkedin"
    TRUST_SOURCE = "trust_source"
