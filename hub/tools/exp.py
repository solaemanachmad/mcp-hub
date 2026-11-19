"""Experiment Orchestrator MCP tools with Kaggle dataset linking."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.db import db
from hub.services import exp as exp_svc


def register(mcp: FastMCP) -> None:
    """Attach distributed experiment orchestration tools to FastMCP."""

    @mcp.tool()
    async def list_nodes() -> dict[str, Any]:
        """List registered compute nodes (mac, pc, kaggle) and their online status."""
        nodes = await db.list_nodes()
        return {"count": len(nodes), "nodes": nodes}

    @mcp.tool()
    async def submit_exp(
        project: str,
        name: str,
        target_node: str = "auto",
        dataset_slug: str = "",
        kaggle_datasets: list[str] | None = None,
        script: str = "",
        config: dict[str, Any] | None = None,
        created_by: str = "ai",
    ) -> dict[str, Any]:
        """Queue an experiment job on Kaggle GPU, Windows 11 PC, or Mac mini M4.

        If `dataset_slug` points to a dataset stored on Kaggle (or `kaggle_datasets` is provided),
        `target_node='auto'` automatically routes the experiment to Kaggle GPU and injects the
        `/kaggle/input/...` mount path into `config`.
        """
        return await exp_svc.submit_experiment(
            project=project,
            name=name,
            target_node=target_node,
            script=script,
            config=config or {},
            dataset_slug=dataset_slug,
            kaggle_datasets=kaggle_datasets,
            created_by=created_by,
        )

    @mcp.tool()
    async def exp_status(exp_id: str) -> dict[str, Any]:
        """Check status and recent log tail for a queued or running experiment."""
        exp = await db.get_experiment(exp_id)
        if not exp:
            return {"error": f"Experiment '{exp_id}' not found."}
        return {
            "id": exp["id"],
            "project": exp["project_slug"],
            "name": exp["name"],
            "node": exp["target_node"],
            "dataset": exp.get("dataset_slug", ""),
            "kaggle_datasets": exp.get("kaggle_datasets", []),
            "status": exp["status"],
            "metrics": exp["metrics"],
            "log_tail": (exp.get("logs") or "")[-1500:],
        }

    @mcp.tool()
    async def exp_result(exp_id: str) -> dict[str, Any]:
        """Fetch full configuration, evaluation metrics, and artifact URL for an experiment."""
        exp = await db.get_experiment(exp_id)
        if not exp:
            return {"error": f"Experiment '{exp_id}' not found."}
        return exp

    @mcp.tool()
    async def compare_exps(project: str, metric: str = "f1", limit: int = 10) -> dict[str, Any]:
        """Compare experiments in a project sorted by a target metric (highest first)."""
        return await exp_svc.compare_experiments(project=project, metric=metric, limit=limit)
