import secrets

from fastapi import Request

from app.services.capability import CSRF_HEADER_NAME


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def validate_csrf_token(request: Request, expected_token: str) -> bool:
    provided = request.headers.get(CSRF_HEADER_NAME)
    if not provided:
        return False
    return secrets.compare_digest(provided, expected_token)
