"""Kaggle MCP tools for dataset discovery, kernel manifest generation, and status tracking."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.db import db
from hub.services.kaggle import kaggle_service


def register(mcp: FastMCP) -> None:
    """Attach Kaggle integration tools to the unified FastMCP server."""

    @mcp.tool()
    async def kaggle_datasets(query: str, limit: int = 5) -> dict[str, Any]:
        """Search Datasets on Kaggle by keyword."""
        try:
            items = await kaggle_service.search_datasets(query=query, limit=limit)
            return {"query": query, "count": len(items), "datasets": items}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    async def kaggle_manifest(
        exp_id: str,
        kernel_id: str = "your-kaggle-username/mcp-hub-runner",
        enable_gpu: bool = True,
    ) -> dict[str, Any]:
        """Build a Kaggle kernel-metadata.json with dataset_sources auto-filled from the experiment's Kaggle datasets."""
        exp = await db.get_experiment(exp_id)
        if not exp:
            return {"error": f"Experiment '{exp_id}' not found."}

        dataset_sources = list(exp.get("kaggle_datasets") or [])
        if exp.get("dataset_slug"):
            ds = await db.get_dataset(exp["dataset_slug"])
            if ds and ds.get("kaggle_ref") and ds["kaggle_ref"] not in dataset_sources:
                dataset_sources.append(ds["kaggle_ref"])

        manifest = {
            "id": kernel_id,
            "title": kernel_id.partition("/")[2].replace("-", " ").title() or "MCP Hub Runner",
            "code_file": "template.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": enable_gpu,
            "enable_tpu": False,
            "enable_internet": True,
            "dataset_sources": dataset_sources,
            "competition_sources": [],
            "kernel_sources": [],
        }
        return {"exp_id": exp_id, "manifest": manifest}

    @mcp.tool()
    async def kaggle_status(kernel_slug: str) -> dict[str, Any]:
        """Check execution status of a Kaggle kernel ('username/kernel-slug')."""
        try:
            return await kaggle_service.kernel_status(kernel_slug)
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    async def kaggle_output(kernel_slug: str) -> dict[str, Any]:
        """List output artifact files produced by a completed Kaggle kernel."""
        try:
            return await kaggle_service.kernel_output(kernel_slug)
        except Exception as exc:
            return {"error": str(exc)}
