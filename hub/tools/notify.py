"""Notification MCP tool for sending Telegram or Webhook alerts."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.services import notify as notify_svc


def register(mcp: FastMCP) -> None:
    """Attach alert tools to the unified FastMCP server."""

    @mcp.tool()
    async def send_alert(title: str, message: str) -> dict[str, Any]:
        """Send an instant notification to your Telegram phone chat or Discord/Slack webhook."""
        return await notify_svc.send_alert(title=title, message=message)
