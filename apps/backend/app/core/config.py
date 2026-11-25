"""Application settings, loaded from environment variables (12-factor)."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DevSecOps360"
    environment: str = Field(default="development", description="development|staging|production")
    app_version: str = "1.0.0"
    # Blue-Green identity: which colour this replica belongs to.
    app_color: str = "blue"

    database_url: str = "sqlite:///./devsecops360.db"

    # JWT — the secret MUST be provided outside development.
    jwt_secret_key: str = Field(default="dev-only-insecure-secret-change-me-0123456789")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    log_level: str = "INFO"

    # Bootstrap admin created by the seed script (never hardcoded).
    admin_email: str | None = None
    admin_password: str | None = None

    # Simple brute-force protection for /auth/login
    login_rate_limit_per_minute: int = 10

    @field_validator("environment")
    @classmethod
    def _env(cls, v: str) -> str:
        allowed = {"development", "test", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_production_safety(self) -> None:
        """Fail fast if an insecure default leaks into staging/production."""
        if self.environment in {"staging", "production"}:
            if self.jwt_secret_key.startswith("dev-only") or len(self.jwt_secret_key) < 32:
                raise RuntimeError("JWT_SECRET_KEY must be set to a strong value (>=32 chars)")
            if self.database_url.startswith("sqlite"):
                raise RuntimeError("SQLite is not allowed outside development/test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
