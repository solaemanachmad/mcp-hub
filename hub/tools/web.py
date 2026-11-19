"""Web Reader & Context7 Live Documentation MCP tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.services import web as web_svc


def register(mcp: FastMCP) -> None:
    """Attach Context7 live documentation and web fetching tools to FastMCP."""

    @mcp.tool()
    async def search_docs(library: str, topic: str = "", max_chars: int = 6000) -> dict[str, Any]:
        """Fetch live, up-to-date documentation for a library/framework via Context7 (with PyPI fallback).

        Args:
            library: Package or framework name (e.g. 'pytorch', 'fastapi', 'timm', 'scikit-learn').
            topic: Optional specific function, class, or feature to focus on.
            max_chars: Maximum characters to return.
        """
        return await web_svc.search_docs(library=library, topic=topic, max_chars=max_chars)

    @mcp.tool()
    async def fetch_page(url: str, max_chars: int = 8000) -> dict[str, Any]:
        """Fetch any web URL or documentation page and convert HTML into clean, compact plain text."""
        return await web_svc.fetch_page(url=url, max_chars=max_chars)
