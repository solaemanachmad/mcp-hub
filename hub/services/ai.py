"""OpenAI-compatible cloud AI & embedding API client (OpenAI, Gemini, Qwen, DeepSeek, OpenRouter)."""

from __future__ import annotations

from typing import Any

import httpx

from hub.config import get_settings


class AIClient:
    """Calls any OpenAI-compatible /chat/completions and /embeddings API directly from Oracle Cloud."""

    def is_configured(self) -> bool:
        return bool(get_settings().ai_api_key.strip())

    def _headers(self) -> dict[str, str]:
        cfg = get_settings()
        if not cfg.ai_api_key:
            raise RuntimeError("AI_API_KEY is not configured in .env.")
        return {
            "Authorization": f"Bearer {cfg.ai_api_key}",
            "Content-Type": "application/json",
        }

    def _base(self) -> str:
        return get_settings().ai_base_url.rstrip("/")

    async def chat(self, prompt: str, system: str = "", model: str = "") -> dict[str, Any]:
        cfg = get_settings()
        chosen = model.strip() or cfg.ai_model
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=float(cfg.ai_timeout)) as client:
            resp = await client.post(
                f"{self._base()}/chat/completions",
                headers=self._headers(),
                json={"model": chosen, "messages": messages, "temperature": 0.2},
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices") or [{}]
        reply = ((choices[0].get("message") or {}).get("content") or "").strip()
        usage = data.get("usage") or {}
        return {
            "model": chosen,
            "reply": reply,
            "tokens": usage.get("total_tokens", 0),
        }

    async def summarize(
        self,
        text: str,
        focus: str = "key findings, methodology, dataset, and metrics",
        max_words: int = 200,
    ) -> dict[str, Any]:
        system = (
            f"You are a concise research assistant. Summarize the text focusing on {focus}. "
            f"Keep the summary under {max_words} words using clear bullet points."
        )
        res = await self.chat(prompt=text[:28000], system=system)
        return {"model": res["model"], "summary": res["reply"], "tokens": res["tokens"]}

    async def embed(self, texts: list[str], model: str = "") -> list[list[float]]:
        """Generate vector embeddings sized to EMBEDDING_DIM (default 768)."""
        if not texts:
            return []
        cfg = get_settings()
        chosen = model.strip() or cfg.embed_model
        payload: dict[str, Any] = {
            "model": chosen,
            "input": texts,
            "dimensions": cfg.embedding_dim,
        }
        async with httpx.AsyncClient(timeout=float(cfg.ai_timeout)) as client:
            resp = await client.post(
                f"{self._base()}/embeddings",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code == 400:
                # Some providers do not accept the optional 'dimensions' field
                payload.pop("dimensions", None)
                resp = await client.post(
                    f"{self._base()}/embeddings",
                    headers=self._headers(),
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json().get("data", [])

        vectors: list[list[float]] = []
        dim = cfg.embedding_dim
        for item in data:
            vec = list(item.get("embedding") or [])
            if len(vec) > dim:
                vec = vec[:dim]
            elif len(vec) < dim:
                vec.extend([0.0] * (dim - len(vec)))
            vectors.append(vec)
        return vectors


ai_client = AIClient()
