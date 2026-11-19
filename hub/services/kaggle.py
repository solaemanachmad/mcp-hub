"""Kaggle REST API client for dataset discovery and kernel monitoring."""

from __future__ import annotations

from typing import Any

import httpx

from hub.config import get_settings


class KaggleService:
    """Thin async wrapper around the Kaggle v1 REST API."""

    BASE_URL = "https://www.kaggle.com/api/v1"

    def _auth(self) -> tuple[str, str]:
        settings = get_settings()
        if not settings.kaggle_username or not settings.kaggle_key:
            raise RuntimeError(
                "Kaggle credentials not configured. Set KAGGLE_USERNAME and KAGGLE_KEY in .env."
            )
        return (settings.kaggle_username, settings.kaggle_key)

    async def search_datasets(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        auth = self._auth()
        params = {"search": query, "page": 1}
        async with httpx.AsyncClient(timeout=20.0, auth=auth) as client:
            resp = await client.get(f"{self.BASE_URL}/datasets/list", params=params)
            resp.raise_for_status()
            items = resp.json()[: max(1, min(limit, 20))]

        return [
            {
                "ref": item.get("ref", ""),
                "title": item.get("title", ""),
                "size_bytes": item.get("totalBytes", 0),
                "downloads": item.get("downloadCount", 0),
                "url": f"https://www.kaggle.com/datasets/{item.get('ref', '')}",
            }
            for item in items
        ]

    async def kernel_status(self, kernel_slug: str) -> dict[str, Any]:
        """Check status of a Kaggle kernel (format: 'username/kernel-slug')."""
        auth = self._auth()
        owner, _, slug = kernel_slug.partition("/")
        if not owner or not slug:
            raise ValueError("kernel_slug must follow 'username/kernel-slug' format.")
        async with httpx.AsyncClient(timeout=20.0, auth=auth) as client:
            resp = await client.get(
                f"{self.BASE_URL}/kernels/status",
                params={"userName": owner, "kernelSlug": slug},
            )
            resp.raise_for_status()
            return resp.json()

    async def kernel_output(self, kernel_slug: str) -> dict[str, Any]:
        """List output artifacts produced by a Kaggle kernel run."""
        auth = self._auth()
        owner, _, slug = kernel_slug.partition("/")
        if not owner or not slug:
            raise ValueError("kernel_slug must follow 'username/kernel-slug' format.")
        async with httpx.AsyncClient(timeout=20.0, auth=auth) as client:
            resp = await client.get(
                f"{self.BASE_URL}/kernels/output",
                params={"userName": owner, "kernelSlug": slug},
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "kernel": kernel_slug,
            "files": [
                {"name": f.get("fileName"), "url": f.get("url")}
                for f in data.get("files", [])
            ],
        }


kaggle_service = KaggleService()
