from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_URL = "postgresql+psycopg://weather:weather@localhost:5432/weather"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL

    @field_validator("database_url")
    @classmethod
    def require_postgresql_url(cls, value: str) -> str:
        """Reject non-PostgreSQL database URLs."""

        if value.startswith("sqlite"):
            raise ValueError(
                "SQLite is not supported; set DATABASE_URL to a PostgreSQL connection string"
            )
        if not value.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must use a PostgreSQL driver (e.g. postgresql+psycopg://...)"
            )
        return value


settings = Settings()

