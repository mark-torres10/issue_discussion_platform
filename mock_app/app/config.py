"""Application configuration and path constants."""

from pathlib import Path

MOCK_APP_ROOT = Path(__file__).resolve().parent.parent

HOST = "127.0.0.1"
PORT = 8765

MOCK_DATA_DIR = MOCK_APP_ROOT / "mock_data"
PROFILES_JSON = MOCK_DATA_DIR / "profiles.json"
PHOTOS_DIR = MOCK_DATA_DIR / "photos"

STATIC_DIR = MOCK_APP_ROOT / "static"
FRONTEND_DIR = MOCK_APP_ROOT / "frontend"

LINKEDIN_UPLOAD_DIR = STATIC_DIR / "uploads" / "linkedin"
TRUST_SOURCE_UPLOAD_DIR = STATIC_DIR / "uploads" / "trust_source"

CURRENT_USER_ID = "user-me"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def ensure_upload_dirs() -> None:
    """Create upload directories if they do not exist."""
    LINKEDIN_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    TRUST_SOURCE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
