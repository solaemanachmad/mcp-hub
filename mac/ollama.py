"""Async Ollama HTTP client for local LLM inference and vector embeddings."""

from __future__ import annotations

from typing import Any

import httpx

from mac.config import get_settings


async def list_models() -> list[str]:
    """Return locally pulled Ollama model names."""
    cfg = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{cfg.ollama_url.rstrip('/')}/api/tags")
        resp.raise_for_status()
        models = resp.json().get("models", [])
    return [m.get("name", "") for m in models]


async def chat(prompt: str, system: str = "", model: str = "") -> dict[str, Any]:
    """Run non-streaming chat completion on local Ollama (default qwen2.5:7b)."""
    cfg = get_settings()
    chosen = model.strip() or cfg.ollama_model
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=float(cfg.ollama_timeout)) as client:
        resp = await client.post(
            f"{cfg.ollama_url.rstrip('/')}/api/chat",
            json={"model": chosen, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "model": chosen,
        "reply": (data.get("message") or {}).get("content", "").strip(),
        "eval_count": data.get("eval_count", 0),
    }


async def embed(texts: list[str], model: str = "") -> list[list[float]]:
    """Generate vector embeddings using Ollama /api/embed (default nomic-embed-text)."""
    if not texts:
        return []
    cfg = get_settings()
    chosen = model.strip() or cfg.embed_model
    async with httpx.AsyncClient(timeout=float(cfg.ollama_timeout)) as client:
        resp = await client.post(
            f"{cfg.ollama_url.rstrip('/')}/api/embed",
            json={"model": chosen, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("embeddings", [])
