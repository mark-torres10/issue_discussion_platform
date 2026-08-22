from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Issue Discussion Platform API")


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Issue Discussion Platform API"}
