from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://genai_app:genai_app@localhost:5432/genai"
    sync_database_url: str = "postgresql+psycopg://genai:genai@localhost:5432/genai"
    test_database_url: str = "postgresql://genai_app:genai_app@localhost:5432/genai"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    jwt_secret_key: str = "dev-local-secret-key-change-before-production-32bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    action_token_expire_minutes: int = 15
    app_public_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
