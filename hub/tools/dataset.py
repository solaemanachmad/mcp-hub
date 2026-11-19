"""Dataset Registry MCP tools with first-class Kaggle dataset linking."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.db import db


def register(mcp: FastMCP) -> None:
    """Attach Dataset Registry tools to the unified FastMCP server."""

    @mcp.tool()
    async def register_dataset(
        slug: str,
        project: str,
        name: str,
        location: str = "kaggle",
        kaggle_ref: str = "",
        mount_path: str = "",
        fmt: str = "csv",
        num_samples: int = 0,
        num_classes: int = 0,
        size_mb: float = 0.0,
        description: str = "",
    ) -> dict[str, Any]:
        """Register or update a dataset in the central catalog (default location='kaggle').

        Args:
            slug: Short dataset ID (e.g. 'gazecom').
            project: Project slug (e.g. 'eye_movement').
            name: Human-readable dataset name.
            location: 'kaggle', 'pc', 'mac', or 'oracle'.
            kaggle_ref: Kaggle dataset reference (e.g. 'username/gazecom-dataset').
            mount_path: Path where compute node reads the dataset (auto-set to '/kaggle/input/<name>' for Kaggle).
            fmt: File format ('csv', 'parquet', 'npy', 'images', 'hdf5').
            num_samples: Number of rows or samples.
            num_classes: Number of target classes.
            size_mb: Approximate dataset size in MB.
            description: Notes on features, preprocessing, or train/test split.
        """
        return await db.upsert_dataset(
            slug=slug,
            project_slug=project,
            name=name,
            location=location,
            kaggle_ref=kaggle_ref,
            mount_path=mount_path,
            fmt=fmt,
            num_samples=num_samples,
            num_classes=num_classes,
            size_mb=size_mb,
            description=description,
        )

    @mcp.tool()
    async def list_datasets(project: str = "", location: str = "") -> dict[str, Any]:
        """List registered datasets filtered by project slug and/or storage location ('kaggle', 'pc', 'mac')."""
        items = await db.list_datasets(project_slug=project, location=location)
        return {"count": len(items), "datasets": items}

    @mcp.tool()
    async def get_dataset(slug: str) -> dict[str, Any]:
        """Get full details, Kaggle reference, and mount path for a registered dataset."""
        ds = await db.get_dataset(slug)
        if not ds:
            return {"error": f"Dataset '{slug}' not found."}
        return ds
