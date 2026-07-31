import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", ".env.override.local"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_ignore_empty=True,
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
    DATABASE_POOL_SIZE: int = Field(default=3, ge=1, le=50)
    DATABASE_MAX_OVERFLOW: int = Field(default=7, ge=0, le=100)
    DATABASE_POOL_TIMEOUT_SECONDS: float = Field(default=10.0, ge=1.0, le=120.0)
    API_RISK_AUDIT_POOL_SIZE: int = Field(default=20, ge=2, le=50)
    API_RISK_AUDIT_MAX_CONCURRENCY: int = Field(default=10, ge=1, le=16)
    REDIS_URL: str = "redis://localhost:6379/0"
    STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_ROOT: Path = Path("./data/storage")
    COS_SECRET_ID: str = ""
    COS_SECRET_KEY: str = ""
    COS_REGION: str = "ap-beijing"
    COS_BUCKET: str = ""
    COS_SCHEME: str = "https"
    COS_PRESIGNED_EXPIRES_SECONDS: int = 600
    COS_UPLOAD_MAX_BYTES: int = 100 * 1024 * 1024
    UPLOAD_GATE_ENABLED: bool = True
    UPLOAD_GATE_SECRET_HASH: str = ""
    UPLOAD_GATE_MAX_BYTES: int = 104857600
    UPLOAD_GATE_ALLOWED_MIME_PREFIXES: list[str] = Field(
        default_factory=lambda: ["image/", "application/pdf", "text/markdown"]
    )
    UPLOAD_GATE_ALLOWED_PREFIXES: list[str] = Field(
        default_factory=lambda: ["uploads/", "tmp/uploads/"]
    )
    UPLOAD_GATE_PRESIGNED_EXPIRES_SECONDS: int = 600
    LLM_PROVIDER: str = "xfyun"
    XFYUN_APP_ID: str = ""
    XFYUN_API_KEY: str = ""
    XFYUN_API_SECRET: str = ""
    XFYUN_BASE_URL: str = "https://spark-api-open.xf-yun.com/v1"
    XFYUN_MODEL: str = "spark-v4"
    XFYUN_THINKING_MODE: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    VOLCENGINE_IMAGE_API_KEY: str = ""
    VOLCENGINE_IMAGE_MODEL: str = "doubao-seedream-5.0-lite"
    VOLCENGINE_IMAGE_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/plan/v3"
    VOLCENGINE_IMAGE_TIMEOUT_SECONDS: float = Field(default=120.0, ge=5.0, le=300.0)
    VOLCENGINE_IMAGE_MAX_BYTES: int = Field(
        default=20 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
    )
    WUYINKEJI_VIDEO_API_KEY: str = ""
    WUYINKEJI_VIDEO_BASE_URL: str = "https://api.wuyinkeji.com"
    WUYINKEJI_VIDEO_MODEL: str = "video_google_omni"
    WUYINKEJI_VIDEO_TIMEOUT_SECONDS: float = Field(default=300.0, ge=10.0, le=600.0)
    WUYINKEJI_VIDEO_POLL_INTERVAL_SECONDS: float = Field(default=5.0, ge=2.0, le=30.0)
    WUYINKEJI_VIDEO_MAX_POLL_ATTEMPTS: int = Field(default=120, ge=10, le=600)
    WUYINKEJI_VIDEO_DEFAULT_SIZE: str = "1280x720"
    WUYINKEJI_VIDEO_DEFAULT_DURATION: str = "10"
    WUYINKEJI_VIDEO_MAX_BYTES: int = Field(
        default=100 * 1024 * 1024,
        ge=1024,
        le=500 * 1024 * 1024,
    )
    # Deliberately omitted from .env.example. This is a 32-byte urlsafe-base64
    # server master key used only for authenticated encryption of user-owned
    # LLM credentials; an empty value fail-closes credential operations.
    PROVIDER_CREDENTIAL_MASTER_KEY: str = ""
    AGENT_RUN_REAL_ENABLED: bool = False
    AGENT_RUN_REAL_MAX_CONCURRENCY: int = Field(default=1, ge=1, le=16)
    AGENT_RUN_REAL_MAX_TOKENS: int = Field(default=800, ge=1, le=4096)
    AGENT_RUN_EVENT_HISTORY_LIMIT: int = Field(default=2048, ge=1, le=10000)
    AGENT_RUN_EVENT_SUBSCRIBER_QUEUE_LIMIT: int = Field(default=256, ge=1, le=4096)
    AGENT_RUN_COMPLETED_TTL_SECONDS: int = Field(default=3600, ge=1, le=86400)
    RUNTIME_SUPERVISOR_ENABLED: bool = True
    EMBEDDING_PROVIDER: str = "qwen_openai_compatible"
    EMBEDDING_MODEL: str = "text-embedding-v4"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_PROFILE: str = "qwen-openai-compatible:text-embedding-v4:1024:dense:v1"
    EMBEDDING_BATCH_SIZE: int = 10
    EMBEDDING_MAX_CONCURRENCY: int = 1
    EMBEDDING_TIMEOUT_SECONDS: float = 30.0
    EMBEDDING_MAX_RETRIES: int = 2
    EMBEDDING_OUTPUT_TYPE: str = "dense"
    ENABLE_EMBEDDING_LIVE_TESTS: bool = False
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL: str = ""
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

    @field_validator("UPLOAD_GATE_ALLOWED_MIME_PREFIXES", "UPLOAD_GATE_ALLOWED_PREFIXES", mode="before")
    @classmethod
    def parse_upload_gate_lists(cls, value: object) -> object:
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

    @field_validator("XFYUN_THINKING_MODE")
    @classmethod
    def validate_xfyun_thinking_mode(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"", "enabled", "disabled", "auto"}:
            raise ValueError("XFYUN_THINKING_MODE must be enabled, disabled, auto, or empty")
        return normalized

    @field_validator("VOLCENGINE_IMAGE_BASE_URL")
    @classmethod
    def validate_volcengine_image_base_url(cls, value: object) -> str:
        normalized = str(value or "").strip().rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("VOLCENGINE_IMAGE_BASE_URL must use https")
        return normalized

    @model_validator(mode="after")
    def validate_storage_config(self) -> "Settings":
        self.STORAGE_PROVIDER = self.STORAGE_PROVIDER.strip().lower()
        self.COS_SCHEME = self.COS_SCHEME.strip().lower()
        if self.STORAGE_PROVIDER == "cos":
            missing = [
                name
                for name in (
                    "COS_SECRET_ID",
                    "COS_SECRET_KEY",
                    "COS_REGION",
                    "COS_BUCKET",
                )
                if not str(getattr(self, name)).strip()
            ]
            if missing:
                raise ValueError(
                    "STORAGE_PROVIDER=cos requires non-empty settings: "
                    + ", ".join(missing)
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
