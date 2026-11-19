"""HTTP client for delegating LLM, embedding, and PDF work to Mac mini M4 via Tailscale."""

from __future__ import annotations

from typing import Any

import httpx

from hub.config import get_settings


class MacClient:
    """Calls the Mac mini M4 Local AI service over private Tailscale network."""

    def _headers(self) -> dict[str, str]:
        settings = get_settings()
        return {"Authorization": f"Bearer {settings.worker_token}"}

    def _base(self) -> str:
        return get_settings().mac_url.rstrip("/")

    def _timeout(self) -> float:
        return float(get_settings().mac_timeout)

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base()}/health")
            resp.raise_for_status()
            return resp.json()

    async def chat(self, prompt: str, system: str = "", model: str = "") -> dict[str, Any]:
        payload = {"prompt": prompt, "system": system, "model": model}
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            resp = await client.post(
                f"{self._base()}/chat",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def summarize(self, text: str, focus: str = "key findings and methodology", max_words: int = 200) -> dict[str, Any]:
        payload = {"text": text, "focus": focus, "max_words": max_words}
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            resp = await client.post(
                f"{self._base()}/summarize",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            resp = await client.post(
                f"{self._base()}/embed",
                json={"texts": texts},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("embeddings", [])

    async def extract_pdf(self, pdf_bytes: bytes, filename: str = "paper.pdf", summarize: bool = True) -> dict[str, Any]:
        files = {"file": (filename, pdf_bytes, "application/pdf")}
        data = {"summarize": "true" if summarize else "false"}
        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            resp = await client.post(
                f"{self._base()}/pdf/extract",
                files=files,
                data=data,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()


mac_client = MacClient()
