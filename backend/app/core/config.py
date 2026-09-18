from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "AI Agentic Research Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/research_agent",
        description="Async PostgreSQL connection string",
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Vector Embedding
    EMBEDDING_DIMENSION: int = Field(
        default=1536,
        description="Embedding vector dimension for pgvector (e.g. 1536 for OpenAI, 768 for small models)",
    )

    # Redis Caching
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_VERSION: str = "v1"
    CACHE_DEFAULT_TTL_SECONDS: int = 300  # 5 minutes
    CACHE_LONG_TTL_SECONDS: int = 3600    # 1 hour
    CACHE_SHORT_TTL_SECONDS: int = 60     # 1 minute
    REDIS_ENABLED: bool = True

    # Security & HTTPS
    FORCE_HTTPS: bool = False
    BEHIND_PROXY: bool = True
    ALLOWED_HOSTS: list[str] = ["*"]
    BCRYPT_MAX_PASSWORD_BYTES: int = 72
    AUTH_RATE_LIMIT_PER_MINUTE: int = 15

    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production-1234567890abcdef"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Object Storage
    STORAGE_PROVIDER: str = "local"  # local, s3, minio, r2
    STORAGE_BUCKET: str = "research-agent-files"
    STORAGE_LOCAL_PATH: str = "/tmp/research_agent_storage"
    STORAGE_ENDPOINT_URL: Optional[str] = None
    STORAGE_ACCESS_KEY: Optional[str] = None
    STORAGE_SECRET_KEY: Optional[str] = None

    # External AI & LLM APIs (Gemini 2.5 Flash, GLM, OpenAI, Tavily)
    LLM_PROVIDER: str = "gemini"  # gemini, glm, openai, local
    LLM_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GLM_API_KEY: Optional[str] = None
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    TAVILY_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None


settings = Settings()
