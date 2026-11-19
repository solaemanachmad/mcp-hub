"""PDF ingestion and semantic RAG search (single-project or cross-project)."""

from __future__ import annotations

import hashlib
import io
from typing import Any

import httpx
from pypdf import PdfReader

from hub.db import Database, db as default_db
from hub.services.mac import MacClient, mac_client as default_mac
from hub.storage import StorageBackend, build_storage


def fallback_chunk_pdf(pdf_bytes: bytes, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    """Local fallback PDF parser if Mac mini M4 is temporarily offline."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    clean = " ".join(full_text.split())
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        chunks.append(clean[start:end])
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return chunks


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
    mac: MacClient | None = None,
    storage: StorageBackend | None = None,
) -> dict[str, Any]:
    """Download or load a PDF, extract/summarize/embed via Mac mini, and persist to DB."""
    repo = database or default_db
    local_ai = mac or default_mac
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

    chunks: list[str] = []
    embeddings: list[list[float] | None] = []
    summary = ""
    processed_by = "mac"

    try:
        extracted = await local_ai.extract_pdf(pdf_bytes, filename=f"{title[:40]}.pdf", summarize=True)
        chunks = extracted.get("chunks", [])
        summary = extracted.get("summary", "")
        if chunks:
            raw_emb = await local_ai.embed(chunks)
            embeddings = raw_emb if len(raw_emb) == len(chunks) else [None] * len(chunks)
    except Exception:
        # Graceful degradation when Mac mini is offline: parse on Hub without embeddings
        processed_by = "hub_fallback"
        chunks = fallback_chunk_pdf(pdf_bytes)
        embeddings = [None] * len(chunks)

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
    mac: MacClient | None = None,
) -> dict[str, Any]:
    """Semantic search over ingested papers (single project, category, or 'all' cross-project)."""
    repo = database or default_db
    local_ai = mac or default_mac
    query_vec: list[float] | None = None
    mode = "vector"

    try:
        vecs = await local_ai.embed([query])
        if vecs:
            query_vec = vecs[0]
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
