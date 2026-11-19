"""Academic paper search across Semantic Scholar, arXiv, and CrossRef."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from hub.config import get_settings


def _truncate(text: str, max_len: int = 320) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3].rstrip() + "..."


async def search_semantic(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Query Semantic Scholar Graph API and return compact paper metadata."""
    settings = get_settings()
    headers = {"User-Agent": f"mcp-hub/0.1 (mailto:{settings.crossref_email})"}
    if settings.semantic_scholar_key:
        headers["x-api-key"] = settings.semantic_scholar_key

    params = {
        "query": query,
        "limit": max(1, min(limit, 20)),
        "fields": "title,authors,year,citationCount,externalIds,url,abstract",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

    results = []
    for item in data:
        authors = [a.get("name", "") for a in item.get("authors", [])[:4]]
        ext = item.get("externalIds") or {}
        results.append(
            {
                "source": "semantic_scholar",
                "title": item.get("title", ""),
                "authors": ", ".join(authors),
                "year": item.get("year"),
                "citations": item.get("citationCount", 0),
                "doi": ext.get("DOI", ""),
                "url": item.get("url", ""),
                "abstract": _truncate(item.get("abstract", "")),
            }
        )
    return results


async def search_arxiv(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Query arXiv Atom API and return compact paper metadata."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max(1, min(limit, 20)),
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get("https://export.arxiv.org/api/query", params=params)
        resp.raise_for_status()

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    results = []
    for entry in root.findall("atom:entry", ns):
        title = " ".join((entry.findtext("atom:title", "", ns)).split())
        summary = _truncate(entry.findtext("atom:summary", "", ns))
        published = entry.findtext("atom:published", "", ns)
        year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
        url = entry.findtext("atom:id", "", ns).strip()
        authors = [
            (a.findtext("atom:name", "", ns) or "").strip()
            for a in entry.findall("atom:author", ns)[:4]
        ]
        results.append(
            {
                "source": "arxiv",
                "title": title,
                "authors": ", ".join(authors),
                "year": year,
                "citations": None,
                "doi": "",
                "url": url,
                "abstract": summary,
            }
        )
    return results


async def search_papers(query: str, limit: int = 5, source: str = "all") -> dict[str, Any]:
    """Search papers with graceful fallback so one API rate-limit never blocks research."""
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    if source in ("all", "semantic_scholar"):
        try:
            results.extend(await search_semantic(query, limit))
        except Exception as exc:
            errors.append(f"semantic_scholar: {exc}")

    if source in ("all", "arxiv") or (source == "all" and not results):
        try:
            results.extend(await search_arxiv(query, limit))
        except Exception as exc:
            errors.append(f"arxiv: {exc}")

    return {"query": query, "count": len(results), "papers": results[: limit * 2], "warnings": errors}


async def lookup_doi(doi: str) -> dict[str, Any]:
    """Fetch verified bibliographic metadata from CrossRef by DOI."""
    settings = get_settings()
    clean_doi = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    headers = {"User-Agent": f"mcp-hub/0.1 (mailto:{settings.crossref_email})"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"https://api.crossref.org/works/{clean_doi}", headers=headers)
        resp.raise_for_status()
        msg = resp.json().get("message", {})

    titles = msg.get("title") or [""]
    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in msg.get("author", [])[:6]
    ]
    issued = msg.get("issued", {}).get("date-parts", [[None]])
    year = issued[0][0] if issued and issued[0] else None
    venue = (msg.get("container-title") or [""])[0]

    return {
        "doi": clean_doi,
        "title": titles[0],
        "authors": ", ".join(authors),
        "year": year,
        "venue": venue,
        "citations": msg.get("is-referenced-by-count", 0),
        "url": msg.get("URL", f"https://doi.org/{clean_doi}"),
    }
