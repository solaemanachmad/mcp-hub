"""PDF ingestion and semantic RAG search running 100% on Oracle Cloud via AI API."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from hub.db import Database, db as default_db
from hub.services import pdf as pdf_svc
from hub.services.ai import AIClient, ai_client as default_ai
from hub.storage import StorageBackend, build_storage


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
    database: Database | None = None,
    ai: AIClient | None = None,
    storage: StorageBackend | None = None,
) -> dict[str, Any]:
    """Download/load a PDF, extract chunks directly on Oracle Cloud, embed/summarize via API, and save to DB."""
    repo = database or default_db
    api = ai or default_ai
    store = storage or build_storage()

    if pdf_url_or_key.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.get(pdf_url_or_key)
            resp.raise_for_status()
            pdf_bytes = resp.content
        digest = hashlib.sha256(pdf_bytes).hexdigest()[:12]
        storage_key = f"papers/{project}/{digest}.pdf"
        store.save(storage_key, pdf_bytes)
        source_url = pdf_url_or_key
    else:
        storage_key = pdf_url_or_key
        pdf_bytes = store.load(storage_key)
        source_url = ""

    full_text, page_count = pdf_svc.extract_text(pdf_bytes)
    chunks = pdf_svc.chunk_text(full_text)
    embeddings: list[list[float] | None] = [None] * len(chunks)
    summary = ""
    processed_by = "text_only"

    if api.is_configured() and chunks:
        try:
            raw_emb = await api.embed(chunks)
            if len(raw_emb) == len(chunks):
                embeddings = raw_emb
                processed_by = "api_embedded"
        except Exception:
            pass

        try:
            sum_res = await api.summarize(full_text[:20000])
            summary = sum_res.get("summary", "")
        except Exception:
            pass

    paper = await repo.save_paper(
        project_slug=project,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        url=source_url,
        summary=summary,
        method=method,
        dataset_used=dataset_used,
        key_metrics=key_metrics,
        limitations=limitations,
        storage_key=storage_key,
    )
    chunk_count = await repo.save_chunks(paper["id"], paper["project_slug"], chunks, embeddings) if chunks else 0

    return {
        "paper_id": paper["id"],
        "project": paper["project_slug"],
        "title": title,
        "pages": page_count,
        "storage_key": storage_key,
        "chunks_stored": chunk_count,
        "processed_by": processed_by,
        "summary": summary,
    }


async def search_kb(
    project: str = "all",
    query: str = "",
    category: str = "",
    top_k: int = 5,
    database: Database | None = None,
    ai: AIClient | None = None,
) -> dict[str, Any]:
    """Semantic search over ingested papers (single project, category, or 'all' cross-project)."""
    repo = database or default_db
    api = ai or default_ai
    query_vec: list[float] | None = None
    mode = "keyword_fallback"

    if api.is_configured():
        try:
            vecs = await api.embed([query])
            if vecs:
                query_vec = vecs[0]
                mode = "vector"
        except Exception:
            mode = "keyword_fallback"

    hits = await repo.search_chunks(
        project_slug=project,
        query_text=query,
        query_embedding=query_vec,
        category=category,
        top_k=max(1, min(top_k, 15)),
    )
    return {
        "project": project,
        "category": category or "all",
        "query": query,
        "mode": mode,
        "count": len(hits),
        "hits": [
            {
                "paper_id": h["paper_id"],
                "project": h["project_slug"],
                "title": h["paper_title"],
                "doi": h["doi"],
                "year": h["year"],
                "score": round(float(h.get("score", 0.0)), 4),
                "excerpt": h["content"][:700],
            }
            for h in hits
        ],
    }
