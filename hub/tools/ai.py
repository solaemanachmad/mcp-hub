"""Cloud AI API delegation tools (fast/low-cost summarization & Q&A directly on Oracle Cloud)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.config import get_settings
from hub.services.ai import ai_client


def register(mcp: FastMCP) -> None:
    """Attach cloud AI helper tools to the unified FastMCP server."""

    @mcp.tool()
    async def ask_ai(prompt: str, system: str = "", model: str = "") -> dict[str, Any]:
        """Run a prompt via the configured fast/low-cost AI API (Gemini Flash, Qwen, GPT-4o-mini, DeepSeek) on Oracle Cloud."""
        return await ai_client.chat(prompt=prompt, system=system, model=model)

    @mcp.tool()
    async def summarize_text(
        text: str,
        focus: str = "key findings, methodology, dataset, and metrics",
        max_words: int = 200,
    ) -> dict[str, Any]:
        """Compress long papers, logs, or text on the server before feeding into your main AI client."""
        return await ai_client.summarize(text=text, focus=focus, max_words=max_words)

    @mcp.tool()
    async def ai_status() -> dict[str, Any]:
        """Check configured AI API provider, chat model, and embedding model on Oracle Cloud."""
        cfg = get_settings()
        return {
            "configured": ai_client.is_configured(),
            "base_url": cfg.ai_base_url,
            "chat_model": cfg.ai_model,
            "embed_model": cfg.embed_model,
            "embedding_dim": cfg.embedding_dim,
        }
