"""Application configuration."""

from pydantic import model_validator
from pydantic_settings import BaseSettings

_INSECURE_JWT_DEFAULTS = {"change-me-in-production", "change-me", "secret", ""}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Development mode — when False, enforces strict security
    dev_mode: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://dyslex:dyslex@localhost:5432/dyslex"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600

    # Redis (for snapshot storage)
    redis_url: str = "redis://localhost:6379/0"
    snapshot_ttl_hours: int = 24  # Ephemeral snapshots expire after 24 hours

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # NVIDIA NIM API
    nvidia_nim_api_key: str = ""
    nvidia_nim_llm_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_voice_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_llm_model: str = "nvidia/nemotron-3-nano-30b-a3b"
    nvidia_nim_vision_model: str = "nvidia/cosmos-reason2-8b"

    # Transcription (local faster-whisper for desktop; not used when browser handles STT)
    transcription_url: str = "http://localhost:8786/v1"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 1 week

    # Rate Limiting
    rate_limit_llm: int = 10  # per user per minute
    rate_limit_voice: int = 20  # per user per minute

    # Correction Routing
    confidence_threshold: float = 0.85

    # LLM Generation (Nemotron supports 32k context)
    llm_max_tokens: int = 16384

    # LLM Tool Calling
    llm_tool_calling_enabled: bool = True
    llm_tool_calling_max_rounds: int = 3

    # TTS Audio Storage
    tts_audio_dir: str = "storage/audio"
    tts_audio_base_url: str = "/audio"
    tts_cache_ttl: int = 3600  # 1 hour
    tts_cleanup_enabled: bool = True

    # File uploads
    max_upload_size_mb: int = 25

    # Logging
    log_level: str = "info"

    @model_validator(mode="after")
    def _validate_production(self) -> "Settings":
        if not self.dev_mode:
            if self.jwt_secret_key in _INSECURE_JWT_DEFAULTS:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a secure value when DEV_MODE=false"
                )
            if len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters when DEV_MODE=false"
                )
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
