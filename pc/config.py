"""Configuration for the Office PC (Windows 11) experiment worker."""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hub_url: str = "http://oracle-cloud:8000"
    worker_token: str = "change-me-worker-token"
    node_name: str = "pc"
    poll_interval: int = 10
    job_timeout: int = 3600
    work_dir: str = "./runs"


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    return WorkerSettings()
