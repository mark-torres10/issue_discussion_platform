import asyncio
import os
import queue
import threading
from collections.abc import Coroutine
from concurrent import futures
from functools import lru_cache
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

T = TypeVar("T")


class _AsyncRunner:
    """Run coroutines on one dedicated event-loop thread."""

    def __init__(self) -> None:
        self._queue: queue.Queue[
            tuple[Coroutine[Any, Any, Any] | None, futures.Future[Any] | None]
        ] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="db-async-runner", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            coro, future = self._queue.get()
            if coro is None:
                loop.close()
                return
            assert future is not None
            try:
                future.set_result(loop.run_until_complete(coro))
            except Exception as exc:  # noqa: BLE001
                future.set_exception(exc)

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        future: futures.Future[T] = futures.Future()
        self._queue.put((coro, future))
        return future.result()


_runner = _AsyncRunner()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    return _runner.run(coro)


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
    if get_engine.cache_info().currsize == 0:
        get_engine.cache_clear()
        return
    engine = get_engine()
    get_engine.cache_clear()
    run_async(engine.dispose())
