import os
from functools import lru_cache


class Settings:
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
    return Settings()
