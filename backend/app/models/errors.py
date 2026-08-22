from pydantic import BaseModel


class ApiError(BaseModel):
    request_id: str
    error_code: str
    message: str
    retryable: bool = False
    retry_after_seconds: int | None = None
    session_status: str | None = None
    current_version: int | None = None
