"""Shared cross-AI project memory so multiple AI clients stay synchronized."""

from __future__ import annotations

from typing import Any

from hub.db import Database, db as default_db


async def get_context(
    project: str,
    limit: int = 8,
    database: Database | None = None,
) -> dict[str, Any]:
    """Return a compact, token-efficient briefing for any AI joining a project."""
    repo = database or default_db
    proj = await repo.ensure_project(project)
    notes = await repo.list_notes(proj["slug"], limit=limit)
    exps = await repo.list_experiments(proj["slug"], limit=5)
    paper_count = await repo.count_papers(proj["slug"])

    return {
        "project": proj["slug"],
        "name": proj["name"],
        "description": proj["description"],
        "paper_count": paper_count,
        "recent_notes": [
            {
                "id": n["id"],
                "title": n["title"],
                "author_ai": n["author_ai"],
                "tags": n["tags"],
                "content": n["content"][:500],
            }
            for n in notes
        ],
        "recent_experiments": [
            {
                "id": e["id"],
                "name": e["name"],
                "node": e["target_node"],
                "status": e["status"],
                "metrics": e["metrics"],
            }
            for e in exps
        ],
    }
