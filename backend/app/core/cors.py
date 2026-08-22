"""CORS middleware registration for the Study API.

Configures allowed browser origins, credentials, methods, and exposed headers
for participant UI requests that send cookies and CSRF tokens.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def register_cors(app: FastAPI) -> None:
    """Attach CORS middleware with deployment-specific allowed origins.

    Reads ``CORS_ALLOWED_ORIGINS`` as a comma-separated list. Defaults to local
    Next.js dev origins. Credentials are allowed and the CSRF header name is
    exposed so browser clients can read it.

    Parameters
    ----------
    app : fastapi.FastAPI
        Application that should accept cross-origin participant UI requests.
    """
    origins_raw = os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )
    origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[CSRF_HEADER_NAME],
    )


from app.services.capability import CSRF_HEADER_NAME  # noqa: E402
