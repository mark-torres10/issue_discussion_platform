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
    return _serializer().dumps(payload)


def load_capability_payload(signed_value: str) -> dict[str, str]:
    return _serializer().loads(signed_value)


def capability_cookie_attributes(*, cross_site: bool) -> dict[str, str | bool | int]:
    return {
        "httponly": True,
        "secure": True,
        "samesite": "none" if cross_site else "lax",
        "path": "/",
    }
