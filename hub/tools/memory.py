"""Shared cross-AI memory & multi-project categorization tools."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.db import db
from hub.services import memory as mem_svc


def register(mcp: FastMCP) -> None:
    """Attach shared memory and project categorization tools to FastMCP."""

    @mcp.tool()
    async def create_project(
        slug: str,
        name: str,
        category: str = "research",
        status: str = "active",
        description: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create or update a project with category ('research', 'ml', 'software', 'teaching') and status ('active', 'paused', 'completed', 'archived')."""
        return await db.ensure_project(
            slug=slug,
            name=name,
            category=category,
            status=status,
            description=description,
            tags=tags or [],
        )

    @mcp.tool()
    async def list_projects(category: str = "", status: str = "") -> dict[str, Any]:
        """List projects optionally filtered by category ('research', 'ml', 'software', 'teaching') and status ('active', 'archived')."""
        projects = await db.list_projects(category=category, status=status)
        return {"count": len(projects), "projects": projects}

    @mcp.tool()
    async def save_note(
        project: str,
        title: str,
        content: str,
        author_ai: str = "unknown",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Save a shared note or decision so any other AI client can resume seamlessly."""
        return await db.save_note(
            project_slug=project,
            title=title,
            content=content,
            author_ai=author_ai,
            tags=tags or [],
        )

    @mcp.tool()
    async def get_context(project: str = "general", limit: int = 8) -> dict[str, Any]:
        """Get a compact project briefing (latest notes, paper count, recent experiments)."""
        return await mem_svc.get_context(project=project, limit=limit)
