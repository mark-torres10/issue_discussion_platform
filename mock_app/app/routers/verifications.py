"""Verification upload HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.profile import VerificationKind
from app.routers.profiles import profile_to_response
from app.services.data_store import get_data_store
from app.services.files import save_upload

router = APIRouter(prefix="/verifications", tags=["verifications"])


def _process_verification(
    kind: VerificationKind,
    photo: UploadFile | None,
    video: UploadFile | None,
) -> dict:
    if photo is None and video is None:
        raise HTTPException(status_code=400, detail="At least one file is required")

    uploaded_urls: list[str] = []
    if photo is not None and photo.filename:
        uploaded_urls.append(save_upload(kind=kind, file=photo, prefix="photo"))
    if video is not None and video.filename:
        uploaded_urls.append(save_upload(kind=kind, file=video, prefix="video"))

    if not uploaded_urls:
        raise HTTPException(status_code=400, detail="At least one file is required")

    store = get_data_store()
    try:
        profile = store.set_verification(kind, verified=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Profile not found") from exc

    response = profile_to_response(profile)
    response["uploaded_urls"] = uploaded_urls
    return response


@router.post("/linkedin")
def linkedin_verification(
    photo: Annotated[UploadFile | None, File()] = None,
    video: Annotated[UploadFile | None, File()] = None,
) -> dict:
    return _process_verification(VerificationKind.LINKEDIN, photo, video)


@router.post("/trust_source")
def trust_source_verification(
    photo: Annotated[UploadFile | None, File()] = None,
    video: Annotated[UploadFile | None, File()] = None,
) -> dict:
    return _process_verification(VerificationKind.TRUST_SOURCE, photo, video)
