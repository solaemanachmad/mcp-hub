"""Experiment Orchestrator routing, Kaggle dataset linking, and comparison logic."""

from __future__ import annotations

from typing import Any

from hub.db import Database, db as default_db


def route_node(
    target_node: str,
    config: dict[str, Any] | None = None,
    dataset_location: str = "",
) -> str:
    """Resolve 'auto' routing based on dataset location and workload hints in config."""
    clean = (target_node or "auto").strip().lower()
    if clean in ("pc", "mac", "kaggle"):
        return clean

    # If the linked dataset lives on Kaggle, default auto-execution to Kaggle GPU!
    if dataset_location.strip().lower() == "kaggle":
        return "kaggle"

    cfg = config or {}
    if cfg.get("gpu") or cfg.get("epochs", 0) >= 20 or cfg.get("accelerator") == "gpu":
        return "kaggle"
    if cfg.get("task") in ("pdf", "embed", "summarize", "llm"):
        return "mac"
    return "pc"


async def submit_experiment(
    project: str,
    name: str,
    target_node: str = "auto",
    script: str = "",
    config: dict[str, Any] | None = None,
    dataset_slug: str = "",
    kaggle_datasets: list[str] | None = None,
    created_by: str = "ai",
    database: Database | None = None,
) -> dict[str, Any]:
    """Queue an experiment, auto-attach Dataset Registry paths, and route to compute node."""
    repo = database or default_db
    merged_cfg = dict(config or {})
    kaggle_refs = list(kaggle_datasets or [])
    ds_location = ""

    if dataset_slug:
        ds = await repo.get_dataset(dataset_slug)
        if ds:
            ds_location = ds.get("location", "")
            merged_cfg.setdefault("dataset_slug", ds["slug"])
            merged_cfg.setdefault("dataset_path", ds.get("mount_path", ""))
            merged_cfg.setdefault("dataset_format", ds.get("format", ""))
            if ds.get("kaggle_ref") and ds["kaggle_ref"] not in kaggle_refs:
                kaggle_refs.append(ds["kaggle_ref"])

    if kaggle_refs and not ds_location:
        ds_location = "kaggle"

    resolved = route_node(target_node, merged_cfg, dataset_location=ds_location)
    exp = await repo.create_experiment(
        project_slug=project,
        name=name,
        target_node=resolved,
        script=script,
        config=merged_cfg,
        dataset_slug=dataset_slug,
        kaggle_datasets=kaggle_refs,
        created_by=created_by,
    )
    return exp


async def compare_experiments(
    project: str,
    metric: str = "f1",
    limit: int = 10,
    database: Database | None = None,
) -> dict[str, Any]:
    """Compare completed experiments in a project ranked by a target metric."""
    repo = database or default_db
    exps = await repo.list_experiments(project, limit=max(limit, 30))

    def _score(item: dict[str, Any]) -> float:
        val = (item.get("metrics") or {}).get(metric)
        try:
            return float(val)
        except (TypeError, ValueError):
            return float("-inf")

    ranked = sorted(exps, key=_score, reverse=True)[:limit]
    return {
        "project": project,
        "ranked_by": metric,
        "count": len(ranked),
        "experiments": [
            {
                "id": e["id"],
                "name": e["name"],
                "node": e["target_node"],
                "dataset": e.get("dataset_slug", ""),
                "status": e["status"],
                metric: (e.get("metrics") or {}).get(metric),
                "metrics": e.get("metrics", {}),
                "artifact_url": e.get("artifact_url", ""),
            }
            for e in ranked
        ],
    }
