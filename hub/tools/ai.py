"""Multi-LLM Router MCP tools: query, compare, and dynamically register LLM providers."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.config import get_settings
from hub.db import db
from hub.services.ai import ai_client


def register(mcp: FastMCP) -> None:
    """Attach Multi-LLM Router tools to the unified FastMCP server."""

    @mcp.tool()
    async def ask_ai(
        prompt: str,
        provider: str = "",
        system: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        """Query any configured LLM provider ('qwen', 'deepseek', 'baidu', 'weixin', 'gemini', 'openai', 'openrouter')."""
        return await ai_client.chat(prompt=prompt, system=system, model=model, provider=provider)

    @mcp.tool()
    async def compare_llms(
        prompt: str,
        providers: list[str] | None = None,
        system: str = "",
    ) -> dict[str, Any]:
        """Run the same prompt across multiple LLMs concurrently (e.g. ['qwen', 'deepseek', 'baidu']) and compare answers."""
        return await ai_client.compare(prompt=prompt, providers=providers, system=system)

    @mcp.tool()
    async def summarize_text(
        text: str,
        focus: str = "key findings, methodology, dataset, and metrics",
        max_words: int = 200,
        provider: str = "",
    ) -> dict[str, Any]:
        """Compress long papers, logs, or text using your chosen LLM provider."""
        return await ai_client.summarize(text=text, focus=focus, max_words=max_words, provider=provider)

    @mcp.tool()
    async def register_llm(
        name: str,
        base_url: str,
        default_model: str,
        api_key_env: str,
        embed_model: str = "",
    ) -> dict[str, Any]:
        """Dynamically add or update an OpenAI-compatible LLM provider without changing code.

        Args:
            name: Short provider ID (e.g. 'kimi', 'glm', 'groq').
            base_url: OpenAI-compatible API base URL (e.g. 'https://api.moonshot.cn/v1').
            default_model: Default chat model ID.
            api_key_env: Name of the environment variable in .env holding the API key.
            embed_model: Optional embedding model ID.
        """
        return await db.upsert_llm_provider(
            name=name,
            base_url=base_url,
            default_model=default_model,
            api_key_env=api_key_env,
            embed_model=embed_model,
        )

    @mcp.tool()
    async def list_llms() -> dict[str, Any]:
        """List all registered LLM providers (Qwen, DeepSeek, Baidu, Weixin, Gemini, OpenAI, etc.) and key status."""
        cfg = get_settings()
        provs = await ai_client.get_providers()
        return {
            "default_provider": cfg.default_provider,
            "embed_provider": cfg.embed_provider,
            "providers": [
                {
                    "name": name,
                    "default_model": p["default_model"],
                    "embed_model": p.get("embed_model", ""),
                    "api_key_env": p["api_key_env"],
                    "active": p.get("has_key", False),
                    "base_url": p["base_url"],
                }
                for name, p in provs.items()
            ],
        }
