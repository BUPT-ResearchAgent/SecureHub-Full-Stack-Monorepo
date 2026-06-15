import json
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "securehub-backend"
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://securehub:securehub@localhost:5432/securehub"
    REDIS_URL: str = "redis://localhost:6379/0"
    LLM_PROVIDER: str = "xfyun"
    XFYUN_APP_ID: str = ""
    XFYUN_API_KEY: str = ""
    XFYUN_API_SECRET: str = ""
    XFYUN_MODEL: str = "spark-v4"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    EMBEDDING_PROVIDER: str = "bge_m3"
    EMBEDDING_DIM: int = 1024
    MIN_EVIDENCE: int = 3
    RETRIEVAL_TOP_K: int = 8
    RERANK_TOP_K: int = 5
    ROUTER_W_CAP: float = 0.35
    ROUTER_W_CTX: float = 0.25
    ROUTER_W_TOOL: float = 0.10
    ROUTER_W_RISK: float = 0.10
    ROUTER_W_HIST: float = 0.20
    ROUTER_MIN_SCORE: float = 0.4
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_HOURS: int = 24

    @field_validator("FRONTEND_ORIGINS", mode="before")
    @classmethod
    def parse_frontend_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "yes"}:
                return True
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
