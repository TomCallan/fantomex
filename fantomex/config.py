from functools import lru_cache
from pathlib import Path

from fastapi import Header, HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./fantomex.db"
    artifact_root: Path = Path("./artifacts")
    log_level: str = "info"
    host: str = "0.0.0.0"
    port: int = 8000

    # API Authentication
    enable_auth: bool = False
    api_key: str | None = None

    # S3 Object Storage
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Ensure settings singleton and local directory initialization
settings = get_settings()
settings.artifact_root.mkdir(parents=True, exist_ok=True)


def verify_api_key(x_api_key: str | None = Header(None, alias="X-Fantomex-Api-Key")):
    cfg = get_settings()
    if cfg.enable_auth:
        if not x_api_key or x_api_key != cfg.api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
