"""Reusable MCP Prompts and full project JSON backup tool."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.db import db


def register(mcp: FastMCP) -> None:
    """Register reusable MCP prompts and project backup/export tools."""

    @mcp.prompt()
    def lit_review(project: str = "eye_movement", topic: str = "CNN and Multi-Head Attention") -> str:
        """Standard workflow prompt for conducting a token-efficient literature review."""
        return (
            f"We are working on project '{project}' focusing on '{topic}'.\n"
            f"1. Call `get_context(project='{project}')` to check existing papers and notes.\n"
            f"2. Call `search_kb(project='{project}', query='{topic}')` and `search_papers(query='{topic}')`.\n"
            f"3. For new papers, summarize via Mac mini (`summarize_local`) and update `paper_matrix(project='{project}')`.\n"
            f"4. Conclude by saving key findings with `save_note(project='{project}', ...)`."
        )

    @mcp.prompt()
    def plan_exp(project: str = "eye_movement", dataset_slug: str = "gazecom", model: str = "TimesNet") -> str:
        """Standard workflow prompt for designing and queuing a Kaggle GPU or PC experiment."""
        return (
            f"Prepare a new experiment for project '{project}' using dataset '{dataset_slug}' and model '{model}'.\n"
            f"1. Call `get_dataset(slug='{dataset_slug}')` and `compare_exps(project='{project}')`.\n"
            f"2. Propose hyperparameters and call `submit_exp(project='{project}', name='{model.lower()}_run', "
            f"dataset_slug='{dataset_slug}', config={{...}})`.\n"
            f"3. If target is Kaggle, generate the kernel manifest with `kaggle_manifest(exp_id=...)`."
        )

    @mcp.prompt()
    def ai_handoff(project: str = "general", current_ai: str = "claude") -> str:
        """Prompt to save a structured session checkpoint before switching to another AI client."""
        return (
            f"Before ending this session on {current_ai}, call `save_note` for project '{project}' "
            f"with `author_ai='{current_ai}'`, summarizing:\n"
            f"- What we completed in this session\n"
            f"- Key decisions or code changes made\n"
            f"- Exact next steps for the next AI (Antigravity, ChatGPT, CodeBuddy, or Qwen) to continue."
        )

    @mcp.tool()
    async def backup_project(project: str) -> dict[str, Any]:
        """Export a complete portable JSON snapshot of a project (notes, papers, datasets, experiments)."""
        proj = await db.ensure_project(project)
        slug = proj["slug"]
        notes = await db.list_notes(slug, limit=200)
        papers = await db.list_papers(slug, limit=200)
        datasets = await db.list_datasets(project_slug=slug)
        exps = await db.list_experiments(slug, limit=200)
        return {
            "project": proj,
            "counts": {
                "notes": len(notes),
                "papers": len(papers),
                "datasets": len(datasets),
                "experiments": len(exps),
            },
            "notes": notes,
            "papers": papers,
            "datasets": datasets,
            "experiments": exps,
        }
