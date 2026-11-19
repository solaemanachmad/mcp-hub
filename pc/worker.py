"""Polling worker daemon for the Office PC (Windows 11: i5 Gen 12, 16GB RAM, 512GB SSD, RX 6600 XT).

Run with:
    python -m pc.worker
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import time
from typing import Any

import httpx

from pc.config import get_settings
from pc.runner import execute_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("pc-worker")


def detect_gpu() -> str:
    """Detect GPU on Windows 11 (e.g. AMD Radeon RX 6600 XT, DirectML, or CUDA)."""
    try:
        if platform.system() == "Windows":
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ', '"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
    except Exception:
        pass
    return "unknown"


def collect_capabilities(work_dir: str) -> dict[str, Any]:
    os.makedirs(work_dir, exist_ok=True)
    disk = shutil.disk_usage(work_dir)
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or "Intel Core i5 Gen 12",
        "cpu_threads": os.cpu_count() or 12,
        "gpu": detect_gpu(),
        "free_disk_gb": round(disk.free / (1024**3), 1),
        "python": platform.python_version(),
    }


def run_loop() -> None:
    cfg = get_settings()
    base = cfg.hub_url.rstrip("/")
    headers = {"Authorization": f"Bearer {cfg.worker_token}"}
    caps = collect_capabilities(cfg.work_dir)

    log.info("Starting PC worker node='%s' hub='%s' gpu='%s'", cfg.node_name, base, caps.get("gpu"))

    with httpx.Client(timeout=30.0, headers=headers) as client:
        while True:
            try:
                client.post(
                    f"{base}/api/nodes/heartbeat",
                    json={
                        "name": cfg.node_name,
                        "kind": "pc",
                        "status": "online",
                        "capabilities": caps,
                    },
                )

                resp = client.post(f"{base}/api/jobs/claim", json={"node": cfg.node_name})
                resp.raise_for_status()
                job = resp.json().get("job")

                if job:
                    log.info("Claimed job %s (%s)", job["id"], job["name"])
                    result = execute_job(job, work_dir=cfg.work_dir, timeout=cfg.job_timeout)
                    client.post(f"{base}/api/jobs/{job['id']}/complete", json=result)
                    log.info("Finished job %s with status=%s", job["id"], result["status"])
                    continue
            except Exception as exc:
                log.warning("Worker loop error: %s", exc)

            time.sleep(cfg.poll_interval)


if __name__ == "__main__":
    run_loop()
