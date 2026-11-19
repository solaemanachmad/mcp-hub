"""Safe subprocess runner for local Python experiments on Windows 11."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def resolve_script(work_root: Path, script: str) -> Path:
    """Resolve a relative script path strictly inside work_root."""
    if not script or not script.strip():
        raise ValueError("Experiment script path is empty.")
    candidate = (work_root / script).resolve()
    root_resolved = work_root.resolve()
    if not str(candidate).startswith(str(root_resolved)):
        raise ValueError(f"Script path escapes work_dir: {script}")
    if not candidate.is_file():
        raise FileNotFoundError(f"Experiment script not found: {candidate}")
    return candidate


def execute_job(job: dict[str, Any], work_dir: str, timeout: int = 3600) -> dict[str, Any]:
    """Execute a claimed experiment job and collect metrics.json + logs."""
    exp_id = job["id"]
    work_root = Path(work_dir).resolve()
    run_dir = work_root / exp_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "config.json"
    metrics_path = run_dir / "metrics.json"
    config_path.write_text(json.dumps(job.get("config") or {}, indent=2), encoding="utf-8")

    try:
        script_path = resolve_script(work_root, job.get("script", ""))
    except Exception as exc:
        return {
            "status": "failed",
            "metrics": {},
            "logs": f"Runner setup error: {exc}",
            "artifact_url": str(run_dir),
        }

    env = os.environ.copy()
    env["EXP_ID"] = exp_id
    env["EXP_CONFIG"] = str(config_path)
    env["EXP_METRICS"] = str(metrics_path)
    env["EXP_RUN_DIR"] = str(run_dir)

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(run_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        logs = (proc.stdout or "") + ("\n--- STDERR ---\n" + proc.stderr if proc.stderr else "")
        metrics: dict[str, Any] = {}
        if metrics_path.is_file():
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logs += f"\nWarning: failed to parse metrics.json: {exc}"

        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "metrics": metrics,
            "logs": logs[-20000:],
            "artifact_url": str(run_dir),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "failed",
            "metrics": {},
            "logs": f"Experiment timed out after {timeout} seconds.",
            "artifact_url": str(run_dir),
        }
