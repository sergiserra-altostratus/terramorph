"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    terramorph_env: str = "development"
    terramorph_log_level: str = "info"
    cors_origins: str = "http://localhost:3000"
    google_application_credentials: str = ""
    job_ttl_seconds: int = 3600  # 1 hour

    @property
    def is_development(self) -> bool:
        return self.terramorph_env == "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
