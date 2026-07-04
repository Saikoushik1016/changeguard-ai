from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="ChangeGuard AI", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    github_webhook_secret: str = Field(default="replace-me", alias="GITHUB_WEBHOOK_SECRET")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_allowed_events_raw: str = Field(
        default="pull_request,push,pull_request_review",
        alias="GITHUB_ALLOWED_EVENTS",
    )

    @property
    def github_allowed_events(self) -> set[str]:
        return {
            item.strip()
            for item in self.github_allowed_events_raw.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()