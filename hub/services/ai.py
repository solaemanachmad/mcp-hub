"""Multi-LLM Router & Embedding API client (Qwen, DeepSeek, Baidu, Weixin/Hunyuan, Gemini, OpenAI, OpenRouter)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from hub.config import get_settings
from hub.db import db

BUILTIN_PROVIDERS: dict[str, dict[str, str]] = {
    "qwen": {
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "embed_model": "text-embedding-v3",
        "api_key_env": "QWEN_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "embed_model": "",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "baidu": {
        "base_url": "https://qianfan.baidubce.com/v2",
        "default_model": "ernie-4.0-8k",
        "embed_model": "embedding-v1",
        "api_key_env": "BAIDU_API_KEY",
    },
    "weixin": {
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "default_model": "hunyuan-pro",
        "embed_model": "hunyuan-embedding",
        "api_key_env": "WEIXIN_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.5-flash",
        "embed_model": "text-embedding-004",
        "api_key_env": "GEMINI_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "embed_model": "text-embedding-3-small",
        "api_key_env": "OPENAI_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "qwen/qwen-2.5-72b-instruct",
        "embed_model": "",
        "api_key_env": "OPENROUTER_API_KEY",
    },
}


def _read_env_key(env_name: str) -> str:
    cfg = get_settings()
    attr = env_name.strip().lower()
    val = getattr(cfg, attr, "") if hasattr(cfg, attr) else ""
    return (val or os.environ.get(env_name, "")).strip()


class AIClient:
    """Multi-provider OpenAI-compatible router for chat, summarization, comparison, and embeddings."""

    async def get_providers(self) -> dict[str, dict[str, Any]]:
        providers = {k: dict(v) for k, v in BUILTIN_PROVIDERS.items()}
        try:
            if db.pool is not None:
                rows = await db.list_llm_providers()
                for r in rows:
                    providers[r["name"]] = dict(r)
        except Exception:
            pass

        for name, info in providers.items():
            key = _read_env_key(info["api_key_env"])
            info["has_key"] = bool(key)
        return providers

    def is_configured(self) -> bool:
        cfg = get_settings()
        if cfg.ai_api_key.strip():
            return True
        return any(
            bool(_read_env_key(info["api_key_env"]))
            for info in BUILTIN_PROVIDERS.values()
        )

    async def _resolve_provider(self, provider: str = "", for_embed: bool = False) -> dict[str, str]:
        cfg = get_settings()
        providers = await self.get_providers()
        requested = (provider or (cfg.embed_provider if for_embed else cfg.default_provider)).strip().lower()

        # 1. Exact requested provider if key is set
        if requested in providers:
            p = providers[requested]
            key = _read_env_key(p["api_key_env"])
            if key and (not for_embed or p.get("embed_model")):
                return {
                    "name": requested,
                    "base_url": p["base_url"].rstrip("/"),
                    "model": p["embed_model"] if for_embed else p["default_model"],
                    "api_key": key,
                }

        # 2. First available provider with a configured key
        for name, p in providers.items():
            key = _read_env_key(p["api_key_env"])
            if key and (not for_embed or p.get("embed_model")):
                return {
                    "name": name,
                    "base_url": p["base_url"].rstrip("/"),
                    "model": p["embed_model"] if for_embed else p["default_model"],
                    "api_key": key,
                }

        # 3. Fallback to generic AI_BASE_URL / AI_API_KEY
        if cfg.ai_api_key.strip():
            return {
                "name": "custom",
                "base_url": cfg.ai_base_url.rstrip("/"),
                "model": cfg.embed_model if for_embed else cfg.ai_model,
                "api_key": cfg.ai_api_key.strip(),
            }

        raise RuntimeError(
            "No LLM API key configured. Set QWEN_API_KEY, DEEPSEEK_API_KEY, BAIDU_API_KEY, "
            "WEIXIN_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, or AI_API_KEY in .env."
        )

    async def chat(
        self,
        prompt: str,
        system: str = "",
        model: str = "",
        provider: str = "",
    ) -> dict[str, Any]:
        cfg = get_settings()
        resolved = await self._resolve_provider(provider, for_embed=False)
        chosen_model = model.strip() or resolved["model"]
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {resolved['api_key']}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=float(cfg.ai_timeout)) as client:
            resp = await client.post(
                f"{resolved['base_url']}/chat/completions",
                headers=headers,
                json={"model": chosen_model, "messages": messages, "temperature": 0.2},
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices") or [{}]
        reply = ((choices[0].get("message") or {}).get("content") or "").strip()
        usage = data.get("usage") or {}
        return {
            "provider": resolved["name"],
            "model": chosen_model,
            "reply": reply,
            "tokens": usage.get("total_tokens", 0),
        }

    async def compare(
        self,
        prompt: str,
        providers: list[str] | None = None,
        system: str = "",
    ) -> dict[str, Any]:
        """Run the same prompt concurrently across multiple LLM providers (e.g. Qwen, DeepSeek, Baidu)."""
        all_provs = await self.get_providers()
        targets = providers or [name for name, p in all_provs.items() if p.get("has_key")]
        if not targets:
            return {"error": "No LLM providers have API keys configured in .env."}

        async def _call_one(prov_name: str) -> dict[str, Any]:
            try:
                return await self.chat(prompt=prompt, system=system, provider=prov_name)
            except Exception as exc:
                return {"provider": prov_name, "error": str(exc)}

        responses = await asyncio.gather(*(_call_one(p) for p in targets))
        return {"prompt": prompt, "count": len(responses), "responses": list(responses)}

    async def summarize(
        self,
        text: str,
        focus: str = "key findings, methodology, dataset, and metrics",
        max_words: int = 200,
        provider: str = "",
    ) -> dict[str, Any]:
        system = (
            f"You are a concise research assistant. Summarize the text focusing on {focus}. "
            f"Keep the summary under {max_words} words using clear bullet points."
        )
        res = await self.chat(prompt=text[:28000], system=system, provider=provider)
        return {
            "provider": res["provider"],
            "model": res["model"],
            "summary": res["reply"],
            "tokens": res["tokens"],
        }

    async def embed(self, texts: list[str], model: str = "", provider: str = "") -> list[list[float]]:
        """Generate vector embeddings sized to EMBEDDING_DIM (default 768)."""
        if not texts:
            return []
        cfg = get_settings()
        resolved = await self._resolve_provider(provider, for_embed=True)
        chosen = model.strip() or resolved["model"]
        headers = {
            "Authorization": f"Bearer {resolved['api_key']}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": chosen,
            "input": texts,
            "dimensions": cfg.embedding_dim,
        }
        async with httpx.AsyncClient(timeout=float(cfg.ai_timeout)) as client:
            resp = await client.post(
                f"{resolved['base_url']}/embeddings",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 400:
                payload.pop("dimensions", None)
                resp = await client.post(
                    f"{resolved['base_url']}/embeddings",
                    headers=headers,
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
