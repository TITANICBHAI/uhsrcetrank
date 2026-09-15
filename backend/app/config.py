from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/uhsrcetrank.db"
    admin_secret: str = ""
    allowed_origin: str = "http://localhost:3000"
    ranking_algorithm_version: str = "v1-UNVERIFIED-placeholder"
    official_url: str = "https://www.uhsrcetadmissions.in/"
    max_upload_bytes: int = 2_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()