from functools import lru_cache
from secrets import token_urlsafe
from typing import List

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="RECRUITPRO_", extra="ignore")

    app_name: str = Field(default="RecruitPro")
    secret_key: SecretStr = Field(
        default_factory=lambda: SecretStr(token_urlsafe(64)),
        validation_alias=AliasChoices("SECRET_KEY", "RECRUITPRO_SECRET_KEY"),
    )
    access_token_expire_minutes: int = Field(default=60, ge=5, le=60 * 24 * 14)
    algorithm: str = Field(default="HS256")
    database_url: str = Field(
        default="sqlite:///./data/recruitpro.db",
        validation_alias=AliasChoices("DATABASE_URL", "RECRUITPRO_DATABASE_URL"),
    )
    storage_path: str = Field(default="storage")
    cors_allowed_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: List[str] | str | None) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def secret_key_value(self) -> str:
        return self.secret_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
