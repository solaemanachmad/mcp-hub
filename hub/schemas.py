"""Pydantic schemas shared across the REST Orchestrator API and services."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class HeartbeatRequest(BaseModel):
    name: str
    kind: str = "pc"
    status: str = "online"
    capabilities: dict[str, Any] = Field(default_factory=dict)


class ExperimentCreate(BaseModel):
    project: str = "general"
    name: str
    target_node: str = "auto"
    dataset_slug: str = ""
    kaggle_datasets: list[str] = Field(default_factory=list)
    script: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "api"


class JobClaimRequest(BaseModel):
    node: str


class JobCompleteRequest(BaseModel):
    status: str = "completed"
    metrics: dict[str, Any] = Field(default_factory=dict)
    logs: str = ""
    artifact_url: str = ""
