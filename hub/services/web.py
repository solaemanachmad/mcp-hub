"""Live documentation search (Context7 / PyPI) and clean HTML-to-text web reader."""

from __future__ import annotations

import html
import re
from typing import Any

import httpx


def html_to_text(raw_html: str, max_chars: int = 8000) -> str:
    """Strip scripts, styles, and HTML tags into clean, token-efficient plain text."""
    cleaned = re.sub(r"(?is)<(script|style|noscript|svg|head).*?>.*?</\1>", " ", raw_html)
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|section|article)>", "\n", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    lines = [" ".join(line.split()) for line in cleaned.splitlines()]
    text = "\n".join(line for line in lines if line)
    return text[:max_chars]


async def fetch_page(url: str, max_chars: int = 8000) -> dict[str, Any]:
    """Fetch a web page or documentation URL and extract clean text."""
    headers = {"User-Agent": "mcp-hub/0.1 (+https://github.com/solaemanachmad/mcp-hub)"}
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        raw = resp.text

    if "html" in content_type.lower() or "<html" in raw[:500].lower():
        text = html_to_text(raw, max_chars=max_chars)
    else:
        text = raw[:max_chars]

    return {
        "url": url,
        "status_code": resp.status_code,
        "length": len(text),
        "content": text,
    }


async def search_docs(library: str, topic: str = "", max_chars: int = 6000) -> dict[str, Any]:
    """Fetch up-to-date library documentation via Context7 API with PyPI metadata fallback."""
    clean_lib = library.strip().lower()
    headers = {"User-Agent": "mcp-hub/0.1"}

    # 1. Try Context7 public search + llms.txt endpoint
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            search_resp = await client.get(
                "https://context7.com/api/v1/search",
                params={"query": clean_lib},
                headers=headers,
            )
            if search_resp.status_code == 200:
                results = search_resp.json().get("results", [])
                if results:
                    top = results[0]
                    lib_id = top.get("id", "").lstrip("/")
                    if lib_id:
                        txt_url = f"https://context7.com/api/v1/{lib_id}/llms.txt"
                        params = {"tokens": 2000}
                        if topic:
                            params["topic"] = topic
                        doc_resp = await client.get(txt_url, params=params, headers=headers)
                        if doc_resp.status_code == 200 and doc_resp.text.strip():
                            return {
                                "source": "context7",
                                "library": top.get("title", clean_lib),
                                "id": lib_id,
                                "topic": topic,
                                "docs": doc_resp.text[:max_chars],
                            }
    except Exception:
        pass

    # 2. Fallback: PyPI JSON API for latest version, summary, and official docs/project URLs
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(f"https://pypi.org/pypi/{clean_lib}/json", headers=headers)
        if resp.status_code != 200:
            return {"error": f"Documentation not found for '{library}' on Context7 or PyPI."}
        info = resp.json().get("info", {})

    return {
        "source": "pypi",
        "library": info.get("name", clean_lib),
        "latest_version": info.get("version", ""),
        "summary": info.get("summary", ""),
        "project_urls": info.get("project_urls") or {},
        "docs": (info.get("description") or "")[:max_chars],
    }
