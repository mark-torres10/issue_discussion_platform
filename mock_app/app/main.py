"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import PHOTOS_DIR
from app.routers import profiles, swipes

app = FastAPI(title="Mock App")

app.include_router(profiles.router, prefix="/api")
app.include_router(swipes.router, prefix="/api")

app.mount("/mock-photos", StaticFiles(directory=PHOTOS_DIR), name="mock-photos")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
