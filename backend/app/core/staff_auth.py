import base64
import hashlib
import hmac
import json
import os
import time
from typing import Annotated

from fastapi import Depends, Request

from app.models.enums import FrozenModel
from app.services.capability import CAPABILITY_COOKIE_NAME
from app.services.sessions import StudyApiError

EXPORT_ALLOWED_ROLES = frozenset({"researcher", "study_admin"})


class StaffIdentity(FrozenModel):
    user_id: str


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _decode_jwt_payload(token: str) -> dict[str, object]:
    parts = token.split(".")
    if len(parts) != 3:
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_required",
            message="Authorization header is required",
        )

    header_b64, payload_b64, signature_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        signature = _b64url_decode(signature_b64)
    except (json.JSONDecodeError, ValueError) as exc:
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_invalid",
            message="Staff JWT is invalid",
        ) from exc

    algorithm = header.get("alg")
    if algorithm != "HS256":
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_invalid",
            message="Staff JWT is invalid",
        )

    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_required",
            message="Staff JWT verification is not configured",
        )

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected_signature, signature):
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_invalid",
            message="Staff JWT is invalid",
        )

    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and time.time() > float(exp):
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_invalid",
            message="Staff JWT is expired",
        )

    return payload


def verify_supabase_jwt(token: str) -> StaffIdentity:
    payload = _decode_jwt_payload(token)
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_invalid",
            message="Staff JWT is invalid",
        )
    return StaffIdentity(user_id=sub)


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def require_staff_identity(request: Request) -> StaffIdentity:
    if request.cookies.get(CAPABILITY_COOKIE_NAME):
        raise StudyApiError(
            status_code=403,
            error_code="staff_forbidden",
            message="Participant capability cannot access staff routes",
        )

    token = _extract_bearer_token(request)
    if not token:
        raise StudyApiError(
            status_code=401,
            error_code="staff_auth_required",
            message="Authorization header is required",
        )
    return verify_supabase_jwt(token)


def require_export_role(role: str) -> None:
    if role not in EXPORT_ALLOWED_ROLES:
        raise StudyApiError(
            status_code=403,
            error_code="staff_forbidden",
            message="Staff membership does not allow this action",
        )


StaffIdentityDep = Annotated[StaffIdentity, Depends(require_staff_identity)]
