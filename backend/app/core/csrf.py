"""CSRF token helpers for participant capability requests.

Generates unpredictable tokens and validates them from request headers using
constant-time comparison.
"""

import secrets

from fastapi import Request

from app.services.capability import CSRF_HEADER_NAME


def generate_csrf_token() -> str:
    """Create a URL-safe CSRF token for a new participant capability.

    Returns
    -------
    str
        A 32-byte random token encoded for safe use in cookies and headers.
    """
    return secrets.token_urlsafe(32)


def validate_csrf_token(request: Request, expected_token: str) -> bool:
    """Check whether the request carries the expected CSRF token.

    Parameters
    ----------
    request : fastapi.Request
        Incoming request whose headers are inspected.
    expected_token : str
        Token issued with the participant capability.

    Returns
    -------
    bool
        ``True`` when the CSRF header is present and matches ``expected_token``;
        ``False`` when the header is missing or does not match.
    """
    provided = request.headers.get(CSRF_HEADER_NAME)
    if not provided:
        return False
    return secrets.compare_digest(provided, expected_token)
