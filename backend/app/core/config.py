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


@lru_cache
def get_settings() -> Settings:
    return Settings()
