from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Recommendation System"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"debug", "development", "dev"}:
                return True
            if normalized in {"release", "production", "prod"}:
                return False
        return value

    # Supabase PostgreSQL — set via DATABASE_URL env var on Render / locally in .env
    database_url: str = "postgresql://postgres:postgres@localhost:5432/recsys"

    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.onrender.com",
    ]
    model_dir: str = "./model_artifacts"
    log_level: str = "INFO"
    default_recommendation_k: int = 10
    max_recommendation_k: int = 50
    cold_start_threshold: int = 3


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
