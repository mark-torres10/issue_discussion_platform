"""Upload validation and persistence for verification media."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, UploadFile

from app.config import (
    ALLOWED_IMAGE_TYPES,
    ALLOWED_VIDEO_TYPES,
    LINKEDIN_UPLOAD_DIR,
    MAX_UPLOAD_BYTES,
    TRUST_SOURCE_UPLOAD_DIR,
)
from app.models.profile import VerificationKind

_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}

_KIND_DIRS = {
    VerificationKind.LINKEDIN: LINKEDIN_UPLOAD_DIR,
    VerificationKind.TRUST_SOURCE: TRUST_SOURCE_UPLOAD_DIR,
}

_KIND_URL_PREFIX = {
    VerificationKind.LINKEDIN: "/uploads/linkedin",
    VerificationKind.TRUST_SOURCE: "/uploads/trust_source",
}


def _allowed_types_for_prefix(prefix: str) -> set[str]:
    if prefix == "photo":
        return ALLOWED_IMAGE_TYPES
    if prefix == "video":
        return ALLOWED_VIDEO_TYPES
    raise ValueError(f"Unknown upload prefix: {prefix}")


def save_upload(*, kind: VerificationKind, file: UploadFile, prefix: str) -> str:
    """Validate and persist an uploaded file; return its public URL path."""
    content_type = file.content_type
    allowed = _allowed_types_for_prefix(prefix)
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid content type: {content_type}")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    ext = _CONTENT_TYPE_EXTENSIONS[content_type]
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    upload_dir = _KIND_DIRS[kind]
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(content)

    return f"{_KIND_URL_PREFIX[kind]}/{filename}"
