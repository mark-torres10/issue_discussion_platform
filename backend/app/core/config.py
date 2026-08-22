"""Runtime configuration for the Study API backend.

Reads deployment settings from environment variables and exposes them through
a cached :class:`Settings` instance via :func:`get_settings`.
"""

import os
from functools import lru_cache


class Settings:
    """Deployment settings sourced from environment variables.

    Each property reflects the current process environment. Values are read on
    access, not cached per attribute.

    Attributes
    ----------
    storage_mode : str
        Persistence backend identifier. Defaults to ``memory``; set
        ``STORAGE_MODE=postgres`` for durable storage.
    use_postgres : bool
        ``True`` when ``storage_mode`` is ``postgres``.
    database_url : str or None
        Postgres connection URL from ``DATABASE_URL``. Required when
        ``use_postgres`` is ``True``.
    railway_git_commit_sha : str or None
        Deployed commit SHA from ``RAILWAY_GIT_COMMIT_SHA``, when present.
    trace_export_enabled : bool
        Whether LangSmith trace export is enabled via ``TRACE_EXPORT_ENABLED``.
    langsmith_api_key : str or None
        LangSmith API key from ``LANGSMITH_API_KEY``.
    langsmith_project : str
        LangSmith project name from ``LANGSMITH_PROJECT``.
    langsmith_workspace_id : str or None
        LangSmith workspace ID from ``LANGSMITH_WORKSPACE_ID``.
    """

    @property
    def storage_mode(self) -> str:
        return os.environ.get("STORAGE_MODE", "memory")

    @property
    def use_postgres(self) -> bool:
        return self.storage_mode == "postgres"

    @property
    def database_url(self) -> str | None:
        return os.environ.get("DATABASE_URL")

    @property
    def railway_git_commit_sha(self) -> str | None:
        return os.environ.get("RAILWAY_GIT_COMMIT_SHA")

    @property
    def trace_export_enabled(self) -> bool:
        return os.environ.get("TRACE_EXPORT_ENABLED", "false").lower() in {
            "1",
            "true",
            "yes",
        }

    @property
    def langsmith_api_key(self) -> str | None:
        return os.environ.get("LANGSMITH_API_KEY")

    @property
    def langsmith_project(self) -> str:
        return os.environ.get("LANGSMITH_PROJECT", "issue-discussion-local")

    @property
    def langsmith_workspace_id(self) -> str | None:
        return os.environ.get("LANGSMITH_WORKSPACE_ID")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached :class:`Settings` instance.

    Returns
    -------
    Settings
        Deployment settings for the current process.
    """
    return Settings()
