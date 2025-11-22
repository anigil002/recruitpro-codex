from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe
from typing import List

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SECRET_FILE = APP_ROOT / "data" / ".secret-key"


def _load_or_create_secret() -> SecretStr:
    """Return a stable application secret, generating it if required."""

    try:
        existing = DEFAULT_SECRET_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        existing = ""
    except OSError:
        existing = ""

    if existing:
        return SecretStr(existing)

    DEFAULT_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    generated = token_urlsafe(64)
    DEFAULT_SECRET_FILE.write_text(generated, encoding="utf-8")
    return SecretStr(generated)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="RECRUITPRO_", extra="ignore")

    app_name: str = Field(default="RecruitPro")
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "RECRUITPRO_ENVIRONMENT"),
    )
    secret_key: SecretStr = Field(
        default_factory=_load_or_create_secret,
        validation_alias=AliasChoices("SECRET_KEY", "RECRUITPRO_SECRET_KEY"),
    )
    access_token_expire_minutes: int = Field(default=60, ge=5, le=60 * 24 * 14)
    algorithm: str = Field(default="HS256")
    database_url: str = Field(
        default="sqlite:///./data/recruitpro.db",
        validation_alias=AliasChoices("DATABASE_URL", "RECRUITPRO_DATABASE_URL"),
    )
    storage_path: str = Field(default="storage")
    cors_allowed_origins: List[str] | str | None = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "RECRUITPRO_GEMINI_API_KEY"),
    )
    google_search_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "RECRUITPRO_GOOGLE_API_KEY"),
    )
    google_custom_search_engine_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GOOGLE_CSE_ID",
            "GOOGLE_CUSTOM_SEARCH_ENGINE_ID",
            "RECRUITPRO_GOOGLE_CSE_ID",
        ),
    )
    smartrecruiters_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SMARTRECRUITERS_EMAIL",
            "RECRUITPRO_SMARTRECRUITERS_EMAIL",
        ),
    )
    smartrecruiters_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SMARTRECRUITERS_PASSWORD",
            "RECRUITPRO_SMARTRECRUITERS_PASSWORD",
        ),
    )
    smartrecruiters_company_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "SMARTRECRUITERS_COMPANY_ID",
            "RECRUITPRO_SMARTRECRUITERS_COMPANY_ID",
        ),
    )
    smartrecruiters_base_url: str = Field(
        default="https://app.smartrecruiters.com",
        validation_alias=AliasChoices(
            "SMARTRECRUITERS_BASE_URL",
            "RECRUITPRO_SMARTRECRUITERS_BASE_URL",
        ),
    )

    # Background Queue (Redis + RQ)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "RECRUITPRO_REDIS_URL"),
    )

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_default: str = Field(default="100/minute")

    # Monitoring & Observability
    sentry_dsn: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SENTRY_DSN", "RECRUITPRO_SENTRY_DSN"),
    )
    sentry_environment: str = Field(default="production")
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)

    # Security Settings
    force_https: bool = Field(default=False)
    password_history_count: int = Field(default=5, ge=0, le=50)

    @field_validator("storage_path", mode="before")
    @classmethod
    def _normalize_storage_path(cls, value: str | None) -> str:
        candidate = Path(value) if value else APP_ROOT / "storage"
        if not candidate.is_absolute():
            candidate = (APP_ROOT / candidate).resolve()
        return str(candidate)

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

    @property
    def resolved_database_path(self) -> Path | None:
        """Return the absolute path to the SQLite database when applicable."""

        try:
            from sqlalchemy.engine import make_url  # Lazy import to avoid early dependency issues
        except Exception:  # pragma: no cover - defensive guard
            return None

        try:
            url = make_url(self.database_url)
        except Exception:  # pragma: no cover - invalid configuration
            return None

        if url.get_backend_name() != "sqlite":
            return None

        database = url.database or ""
        if not database:
            return None

        candidate = Path(database)
        if not candidate.is_absolute():
            candidate = (APP_ROOT / candidate).resolve()
        return candidate

    @staticmethod
    def _secret_value(secret: SecretStr | None) -> str:
        return secret.get_secret_value() if secret else ""

    @property
    def gemini_api_key_value(self) -> str:
        return self._secret_value(self.gemini_api_key)

    @property
    def google_search_api_key_value(self) -> str:
        return self._secret_value(self.google_search_api_key)

    @property
    def smartrecruiters_password_value(self) -> str:
        return self._secret_value(self.smartrecruiters_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
