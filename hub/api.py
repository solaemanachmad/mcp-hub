"""REST API for the Experiment Orchestrator, compute workers, and file uploads."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from hub.db import db
from hub.schemas import ExperimentCreate, HeartbeatRequest, JobClaimRequest, JobCompleteRequest
from hub.services import exp as exp_svc
from hub.services import notify as notify_svc
from hub.storage import build_storage

router = APIRouter(prefix="/api", tags=["orchestrator"])


@router.post("/nodes/heartbeat")
async def node_heartbeat(payload: HeartbeatRequest) -> dict[str, Any]:
    """Register or refresh a compute worker heartbeat (mac, pc, kaggle)."""
    return await db.upsert_node(
        name=payload.name,
        kind=payload.kind,
        status=payload.status,
        capabilities=payload.capabilities,
    )


@router.get("/nodes")
async def get_nodes() -> dict[str, Any]:
    nodes = await db.list_nodes()
    return {"count": len(nodes), "nodes": nodes}


@router.post("/jobs")
async def create_job(payload: ExperimentCreate) -> dict[str, Any]:
    """Queue a new experiment via REST API."""
    return await exp_svc.submit_experiment(
        project=payload.project,
        name=payload.name,
        target_node=payload.target_node,
        script=payload.script,
        config=payload.config,
        dataset_slug=payload.dataset_slug,
        kaggle_datasets=payload.kaggle_datasets,
        created_by=payload.created_by,
    )


@router.post("/jobs/claim")
async def claim_job(payload: JobClaimRequest) -> dict[str, Any]:
    """Claim the next queued job for a compute node (PC, Mac, or Kaggle notebook)."""
    job = await db.claim_experiment(payload.node)
    return {"job": job}


@router.get("/jobs/{exp_id}")
async def get_job(exp_id: str) -> dict[str, Any]:
    """Fetch experiment config and status (used by Kaggle pull-based notebooks)."""
    exp = await db.get_experiment(exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found.")
    return exp


@router.post("/jobs/{exp_id}/complete")
async def complete_job(exp_id: str, payload: JobCompleteRequest) -> dict[str, Any]:
    """Report experiment metrics, logs, and artifact link back to Oracle Cloud + fire Telegram/Webhook alert."""
    updated = await db.complete_experiment(
        exp_id=exp_id,
        status=payload.status,
        metrics=payload.metrics,
        logs=payload.logs,
        artifact_url=payload.artifact_url,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Experiment '{exp_id}' not found.")
    await notify_svc.notify_experiment_done(updated)
    return updated


@router.post("/files/upload")
async def upload_file(
    project: str = Form("general"),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload a PDF or artifact into configured hybrid storage (local or Oracle S3)."""
    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()[:12]
    safe_name = (file.filename or "document.bin").replace("/", "_").replace("..", "")
    key = f"uploads/{project}/{digest}_{safe_name}"
    store = build_storage()
    store.save(key, content)
    return {"storage_key": key, "size_bytes": len(content), "project": project}
