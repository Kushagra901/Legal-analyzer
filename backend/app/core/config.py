"""
Configuration Settings.
Parses environment properties and system parameters.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Main settings schema configuration.
    Defines application settings and loaded options.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "Legal Analyzer"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/legal"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    SECRET_KEY: str = "placeholder_secret_key_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook/document-uploaded"
    INTERNAL_SERVICE_TOKEN: str = "placeholder_internal_service_token_change_me"
    FRONTEND_URL: str = "http://localhost:3000"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    SENTRY_DSN: str = ""



settings = Settings()
