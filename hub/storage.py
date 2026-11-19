"""Hybrid file storage: local filesystem volume or S3-compatible Oracle Object Storage."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from hub.config import Settings, get_settings


class StorageBackend(Protocol):
    def save(self, key: str, data: bytes) -> str: ...
    def load(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...


class LocalStorage:
    """Stores files on a local directory or Docker volume."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        clean = key.lstrip("/").replace("..", "")
        target = (self.root / clean).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Invalid storage key path")
        return target

    def save(self, key: str, data: bytes) -> str:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return key

    def load(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class S3Storage:
    """S3-compatible storage backend (Oracle Object Storage, R2, MinIO)."""

    def __init__(self, settings: Settings) -> None:
        import boto3

        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    def save(self, key: str, data: bytes) -> str:
        clean = key.lstrip("/")
        self.client.put_object(Bucket=self.bucket, Key=clean, Body=data)
        return clean

    def load(self, key: str) -> bytes:
        clean = key.lstrip("/")
        obj = self.client.get_object(Bucket=self.bucket, Key=clean)
        return obj["Body"].read()

    def exists(self, key: str) -> bool:
        clean = key.lstrip("/")
        try:
            self.client.head_object(Bucket=self.bucket, Key=clean)
            return True
        except Exception:
            return False


def build_storage(settings: Settings | None = None) -> StorageBackend:
    """Instantiate configured storage backend."""
    cfg = settings or get_settings()
    if cfg.storage_mode.lower() == "s3" and cfg.s3_bucket:
        return S3Storage(cfg)
    return LocalStorage(cfg.storage_dir)
