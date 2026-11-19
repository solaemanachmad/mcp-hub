"""Lightweight sync client for Kaggle GPU notebooks to pull configs and push metrics."""

from __future__ import annotations

import os
from typing import Any

import httpx


class HubClient:
    """Connects a Kaggle notebook to the Oracle Cloud MCP Hub over HTTPS."""

    def __init__(self, hub_url: str | None = None, worker_token: str | None = None) -> None:
        self.base = (hub_url or os.environ["HUB_URL"]).rstrip("/")
        self.token = worker_token or os.environ["WORKER_TOKEN"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def heartbeat(self, gpu: str = "T4") -> dict[str, Any]:
        with httpx.Client(timeout=20.0, headers=self.headers) as client:
            resp = client.post(
                f"{self.base}/api/nodes/heartbeat",
                json={
                    "name": "kaggle",
                    "kind": "kaggle",
                    "status": "online",
                    "capabilities": {"gpu": gpu},
                },
            )
            resp.raise_for_status()
            return resp.json()

    def claim(self) -> dict[str, Any] | None:
        """Claim the next queued Kaggle experiment from Oracle Cloud."""
        with httpx.Client(timeout=20.0, headers=self.headers) as client:
            resp = client.post(f"{self.base}/api/jobs/claim", json={"node": "kaggle"})
            resp.raise_for_status()
            return resp.json().get("job")

    def pull(self, exp_id: str) -> dict[str, Any]:
        """Pull a specific experiment configuration by ID."""
        with httpx.Client(timeout=20.0, headers=self.headers) as client:
            resp = client.get(f"{self.base}/api/jobs/{exp_id}")
            resp.raise_for_status()
            return resp.json()

    def complete(
        self,
        exp_id: str,
        metrics: dict[str, Any],
        status: str = "completed",
        logs: str = "",
        artifact_url: str = "",
    ) -> dict[str, Any]:
        """Push evaluation metrics, logs, and Kaggle artifact link back to Oracle Cloud."""
        with httpx.Client(timeout=30.0, headers=self.headers) as client:
            resp = client.post(
                f"{self.base}/api/jobs/{exp_id}/complete",
                json={
                    "status": status,
                    "metrics": metrics,
                    "logs": logs,
                    "artifact_url": artifact_url,
                },
            )
            resp.raise_for_status()
            return resp.json()
