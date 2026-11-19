"""Configuration for the Mac mini M4 (16GB) Local AI service."""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class MacSettings(BaseSettings):
    """Settings tuned for Apple Silicon M4 with 16GB unified memory."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mac_host: str = "0.0.0.0"
    mac_port: int = 8100
    worker_token: str = "change-me-worker-token"

    # Optional Hub URL to send periodic online heartbeats
    hub_url: str = ""

    # Ollama defaults sized for 16GB unified memory (~5GB LLM + ~0.3GB embed)
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    embed_model: str = "nomic-embed-text"
    ollama_timeout: int = 180


@lru_cache(maxsize=1)
def get_settings() -> MacSettings:
    return MacSettings()
