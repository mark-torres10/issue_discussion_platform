import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def get_database_url() -> str | None:
    return os.environ.get("DATABASE_URL")


@lru_cache
def get_engine() -> AsyncEngine:
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return create_async_engine(_normalize_database_url(database_url), pool_pre_ping=True)


def reset_engine() -> None:
    get_engine.cache_clear()
