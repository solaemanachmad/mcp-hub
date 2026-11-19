"""Academic Writer MCP tools: Literature Review Matrix, BibTeX export, and LaTeX/Markdown tables."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.db import db
from hub.services import writer as writer_svc


def register(mcp: FastMCP) -> None:
    """Attach academic writing and literature matrix tools to FastMCP."""

    @mcp.tool()
    async def update_review(
        paper_id: int,
        method: str = "",
        dataset_used: str = "",
        key_metrics: str = "",
        limitations: str = "",
    ) -> dict[str, Any]:
        """Update structured Literature Review Matrix columns for an ingested paper."""
        updated = await db.update_paper_review(
            paper_id=paper_id,
            method=method,
            dataset_used=dataset_used,
            key_metrics=key_metrics,
            limitations=limitations,
        )
        if not updated:
            return {"error": f"Paper ID {paper_id} not found."}
        return updated

    @mcp.tool()
    async def paper_matrix(project: str, fmt: str = "markdown") -> dict[str, Any]:
        """Generate a Literature Review Matrix comparing papers (Method, Dataset, Metrics, Research Gap).

        Args:
            project: Project slug (or 'all').
            fmt: 'markdown' or 'latex'.
        """
        return await writer_svc.build_paper_matrix(project=project, fmt=fmt)

    @mcp.tool()
    async def export_bibtex(project: str) -> dict[str, Any]:
        """Export standard BibTeX (.bib) citations for all papers in a project."""
        return await writer_svc.export_bibtex(project=project)

    @mcp.tool()
    async def exp_table(
        project: str,
        metrics: list[str] | None = None,
        fmt: str = "latex",
        caption: str = "Experimental Results Comparison",
    ) -> dict[str, Any]:
        """Generate a publication-ready LaTeX (booktabs) or Markdown table comparing project experiments."""
        return await writer_svc.build_exp_table(
            project=project,
            metrics=metrics,
            fmt=fmt,
            caption=caption,
        )
