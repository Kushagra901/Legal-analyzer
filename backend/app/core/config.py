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
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/legal"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = ""
    OLLAMA_MODEL: str = "qwen3:8b"
    SECRET_KEY: str = "placeholder_secret_key_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook/document-uploaded"
    INTERNAL_SERVICE_TOKEN: str = "placeholder_internal_service_token_change_me"
    AUTH_MOCK_TOKEN: str = "mock-token"
    FRONTEND_URL: str = "http://localhost:3000"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    SENTRY_DSN: str = ""

    # Kafka Event Streaming
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PREFIX: str = "legal-analyzer"

    # Databricks / Lakehouse
    DATABRICKS_HOST: str = ""
    DATABRICKS_TOKEN: str = ""
    DATABRICKS_CATALOG: str = "legal_analyzer"

    # SQL Server (optional secondary database)
    SQL_SERVER_CONNECTION_STRING: str = ""

    def validate_production_secrets(self) -> None:
        """
        Validates that critical security secrets are not left as defaults in production.
        Raises RuntimeError if default placeholders or empty values are detected.
        """
        if self.ENVIRONMENT.lower() == "production":
            insecure_secrets = []
            if self.SECRET_KEY in ("", "placeholder_secret_key_change_me_in_production"):
                insecure_secrets.append("SECRET_KEY")
            if self.INTERNAL_SERVICE_TOKEN in ("", "placeholder_internal_service_token_change_me"):
                insecure_secrets.append("INTERNAL_SERVICE_TOKEN")
            if insecure_secrets:
                raise RuntimeError(
                    f"FATAL: Production launch halted. Insecure default secrets detected: {', '.join(insecure_secrets)}. "
                    "Generate 256-bit random keys using: python -c 'import secrets; print(secrets.token_hex(32))'"
                )




settings = Settings()
