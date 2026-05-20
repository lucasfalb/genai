from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://genai_app:genai_app@localhost:5432/genai"
    sync_database_url: str = "postgresql+psycopg://genai:genai@localhost:5432/genai"
    test_database_url: str = "postgresql://genai_app:genai_app@localhost:5432/genai_test"
    database_schema: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "genai_rag"
    jwt_secret_key: str = "dev-local-secret-key-change-before-production-32bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    action_token_expire_minutes: int = 15
    app_public_url: str = "http://localhost:3000"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_secure: bool = False
    smtp_user: str | None = None
    smtp_pass: str | None = None
    smtp_from: str | None = None
    openai_api_key: str | None = None  # dev fallback only; production uses system_settings
    openai_embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    rag_chunk_tokens: int = 512
    rag_chunk_overlap_tokens: int = 64
    rag_top_k: int = 8
    rag_score_threshold: float = 0.35
    rag_indexing_consumer_enabled: bool = True
    ai_config_encryption_key: str = ""  # Fernet key (base64 32-byte) — required in production
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "genai"
    s3_secret_access_key: str = "genai-local-secret"
    s3_bucket_name: str = "genai-rag-documents"
    s3_public_bucket_name: str = "genai-widget-assets"
    s3_region: str = "us-east-1"
    upload_max_bytes: int = 50 * 1024 * 1024  # 50 MB
    geoip_db_path: str | None = None
    geoip_ip_header_names: str = "cf-connecting-ip,x-real-ip,x-forwarded-for"

    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_enabled: bool = False
    otel_service_name: str = "genai-platform"
    genai_env: str = "development"
    otel_resource_attributes: str = ""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
