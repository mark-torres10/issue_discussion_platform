"""Sample invitation tokens for in-memory contract tests."""

import hashlib

# Known writer invitation for demo-campus-speech-001 (min 32 chars).
SAMPLE_WRITER_INVITATION_TOKEN = (
    "demo-campus-speech-001-invitation-token-for-contract-tests"
)

UNKNOWN_INVITATION_TOKEN = "unknown-invitation-token-that-does-not-exist-xyz"


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
