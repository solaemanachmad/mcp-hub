"""Central settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Oracle Cloud MCP Hub."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server & auth
    hub_port: int = 8000
    hub_token: str = "change-me-hub-token"
    worker_token: str = "change-me-worker-token"

    # Database
    database_url: str = "postgresql://mcphub:change-me-db-password@db:5432/mcphub"
    embedding_dim: int = 768

    # Hybrid storage ("local" or "s3")
    storage_mode: str = "local"
    storage_dir: str = "/data/files"
    s3_endpoint: str = ""
    s3_region: str = "ap-singapore-1"
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # Multi-LLM Router settings (Qwen, DeepSeek, Baidu, Weixin/Hunyuan, Gemini, OpenAI, OpenRouter)
    default_provider: str = "qwen"
    embed_provider: str = "qwen"
    ai_timeout: int = 90

    qwen_api_key: str = ""
    deepseek_api_key: str = ""
    baidu_api_key: str = ""
    weixin_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    openrouter_api_key: str = ""

    # Generic fallback provider
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    embed_model: str = "text-embedding-3-small"

    # Research APIs
    semantic_scholar_key: str = ""
    crossref_email: str = "researcher@example.com"

    # Kaggle API
    kaggle_username: str = ""
    kaggle_key: str = ""

    # Telegram & Webhook notifications
    telegram_token: str = ""
    telegram_chat: str = ""
    webhook_url: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
