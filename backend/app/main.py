from fastapi import FastAPI

from app.api.router import api_router
from app.core.errors import register_exception_handlers, register_middleware

app = FastAPI(title="Issue Discussion Platform API")

register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router)
