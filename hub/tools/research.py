"""Research MCP tools: paper search, DOI lookup, PDF ingestion, and cross-project RAG search."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.services import papers as paper_svc
from hub.services import rag as rag_svc


def register(mcp: FastMCP) -> None:
    """Attach research tools to the unified FastMCP server."""

    @mcp.tool()
    async def search_papers(query: str, limit: int = 5, source: str = "all") -> dict[str, Any]:
        """Search academic papers across Semantic Scholar and arXiv."""
        return await paper_svc.search_papers(query=query, limit=limit, source=source)

    @mcp.tool()
    async def lookup_doi(doi: str) -> dict[str, Any]:
        """Look up verified bibliographic metadata for a DOI via CrossRef."""
        return await paper_svc.lookup_doi(doi)

    @mcp.tool()
    async def ingest_pdf(
        project: str,
        title: str,
        pdf_url_or_key: str,
        doi: str = "",
        authors: str = "",
        year: int | None = None,
        method: str = "",
        dataset_used: str = "",
        key_metrics: str = "",
        limitations: str = "",
    ) -> dict[str, Any]:
        """Store a PDF, extract chunks & embeddings on Mac mini M4, and record Literature Review Matrix fields."""
        return await rag_svc.ingest_pdf(
            project=project,
            title=title,
            pdf_url_or_key=pdf_url_or_key,
            doi=doi,
            authors=authors,
            year=year,
            method=method,
            dataset_used=dataset_used,
            key_metrics=key_metrics,
            limitations=limitations,
        )

    @mcp.tool()
    async def search_kb(
        query: str,
        project: str = "all",
        category: str = "",
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Semantic RAG search over ingested PDFs.

        Args:
            query: Question or search phrase.
            project: Specific project slug (e.g. 'eye_movement') or 'all' to search across all projects.
            category: Optional project category filter ('research', 'ml', 'software', 'teaching').
            top_k: Number of top excerpts to return (1-15).
        """
        return await rag_svc.search_kb(
            project=project,
            query=query,
            category=category,
            top_k=top_k,
        )
