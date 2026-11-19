"""Local AI delegation tools routed to Mac mini M4 (Ollama / Qwen) to save cloud tokens."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.services.mac import mac_client


def register(mcp: FastMCP) -> None:
    """Attach Mac mini M4 local AI tools to the unified FastMCP server."""

    @mcp.tool()
    async def ask_local(prompt: str, system: str = "", model: str = "") -> dict[str, Any]:
        """Run a prompt on the local LLM (default Qwen on Mac mini M4) at zero cloud token cost.

        Ideal for drafting, classification, JSON extraction, and repetitive text processing.
        """
        return await mac_client.chat(prompt=prompt, system=system, model=model)

    @mcp.tool()
    async def summarize_local(
        text: str,
        focus: str = "key findings and methodology",
        max_words: int = 200,
    ) -> dict[str, Any]:
        """Compress long logs, papers, or text using local Qwen on Mac mini M4 before reasoning."""
        return await mac_client.summarize(text=text, focus=focus, max_words=max_words)

    @mcp.tool()
    async def mac_status() -> dict[str, Any]:
        """Check health and loaded Ollama models on Mac mini M4 over Tailscale."""
        try:
            return await mac_client.health()
        except Exception as exc:
            return {"status": "offline", "error": str(exc)}
