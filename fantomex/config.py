from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./fantomex.db"
    artifact_root: Path = Path("./artifacts")
    log_level: str = "info"
    host: str = "127.0.0.1"
    port: int = 8000


def get_settings() -> Settings:
    return Settings()


# Ensure artifact root exists at import time in production usage.
settings = get_settings()
settings.artifact_root.mkdir(parents=True, exist_ok=True)
