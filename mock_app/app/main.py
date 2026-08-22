"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import (
    LINKEDIN_UPLOAD_DIR,
    PHOTOS_DIR,
    TRUST_SOURCE_UPLOAD_DIR,
    ensure_upload_dirs,
)
from app.routers import profiles, swipes, verifications


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_upload_dirs()
    yield


app = FastAPI(title="Mock App", lifespan=lifespan)

app.include_router(profiles.router, prefix="/api")
app.include_router(swipes.router, prefix="/api")
app.include_router(verifications.router, prefix="/api")

app.mount("/mock-photos", StaticFiles(directory=PHOTOS_DIR), name="mock-photos")
app.mount(
    "/uploads/linkedin",
    StaticFiles(directory=LINKEDIN_UPLOAD_DIR),
    name="uploads-linkedin",
)
app.mount(
    "/uploads/trust_source",
    StaticFiles(directory=TRUST_SOURCE_UPLOAD_DIR),
    name="uploads-trust-source",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
