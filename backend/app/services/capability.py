"""Signed participant capability cookies and request idempotency helpers."""

import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

CAPABILITY_COOKIE_NAME = "participant_capability"
CSRF_HEADER_NAME = "X-CSRF-Token"
IDEMPOTENCY_HEADER_NAME = "Idempotency-Key"

_DEFAULT_SECRET = "sample-contracts-dev-secret-change-in-production"


def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("CAPABILITY_SIGNING_SECRET", _DEFAULT_SECRET)
    return URLSafeTimedSerializer(secret, salt="participant-capability")


def sign_capability_payload(payload: dict[str, str]) -> str:
    """Return a time-limited signed token for a capability payload."""
    return _serializer().dumps(payload)


def load_capability_payload(signed_value: str) -> dict[str, str]:
    """Verify and decode a signed capability token.

    Raises
    ------
    BadSignature, SignatureExpired
        If the token is invalid or expired.
    """
    return _serializer().loads(signed_value)


def capability_cookie_attributes(*, cross_site: bool) -> dict[str, str | bool | int]:
    """Return HttpOnly cookie attributes for participant capabilities."""
    return {
        "httponly": True,
        "secure": True,
        "samesite": "none" if cross_site else "lax",
        "path": "/",
    }
