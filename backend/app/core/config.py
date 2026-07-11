from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    allow_signup: bool = False
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+asyncpg://quest:quest@localhost:5432/quest_for_health"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "changeme-generate-a-real-secret"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    garmin_token_encryption_key: str = "changeme-generate-a-real-fernet-key"
    weather_lookup_timeout_seconds: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
