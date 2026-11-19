"""Research & Document Management MCP tools: paper search, DOI lookup, PDF ingestion, lifecycle, and RAG."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.db import db
from hub.services import papers as paper_svc
from hub.services import rag as rag_svc


def register(mcp: FastMCP) -> None:
    """Attach research and document management tools to the unified FastMCP server."""

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
        """Store a PDF, extract chunks & embeddings on Oracle Cloud, and record Literature Review Matrix fields."""
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
    async def list_papers(project: str = "all", limit: int = 30) -> dict[str, Any]:
        """List ingested documents/papers in a project (or 'all' across all projects)."""
        items = await db.list_papers(project_slug=project, limit=limit)
        return {"project": project, "count": len(items), "papers": items}

    @mcp.tool()
    async def get_paper(paper_id: int) -> dict[str, Any]:
        """Get full details, summary, review matrix fields, and storage key for an ingested document."""
        item = await db.get_paper(paper_id)
        if not item:
            return {"error": f"Paper ID {paper_id} not found."}
        return item

    @mcp.tool()
    async def delete_paper(paper_id: int) -> dict[str, Any]:
        """Delete an ingested document and its vector chunks from the database."""
        ok = await db.delete_paper(paper_id)
        return {"deleted": ok, "paper_id": paper_id}

    @mcp.tool()
    async def search_kb(
        query: str,
        project: str = "all",
        category: str = "",
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Semantic RAG search over ingested PDFs (within one project, by category, or 'all')."""
        return await rag_svc.search_kb(
            project=project,
            query=query,
            category=category,
            top_k=top_k,
        )
