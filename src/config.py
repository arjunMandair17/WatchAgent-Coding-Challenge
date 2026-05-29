from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str | None = None

    @model_validator(mode="after")
    def resolve_database_url(self) -> "Settings":
        """Build database_url from POSTGRES_* when DATABASE_URL is not set."""

        if self.database_url:
            return self
        if self.postgres_user and self.postgres_db:
            user = quote_plus(self.postgres_user)
            if self.postgres_password:
                password = quote_plus(self.postgres_password)
                url = (
                    f"postgresql+psycopg://{user}:{password}"
                    f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
                )
            else:
                url = (
                    f"postgresql+psycopg://{user}"
                    f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
                )
            object.__setattr__(self, "database_url", url)
            return self
        raise ValueError(
            "Set DATABASE_URL or POSTGRES_USER and POSTGRES_DB in .env"
        )

    @field_validator("database_url")
    @classmethod
    def require_postgresql_url(cls, value: str | None) -> str | None:
        """Reject non-PostgreSQL database URLs."""

        if value is None:
            return value
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
