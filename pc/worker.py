"""Polling worker daemon for the Office PC (Windows 11).

Run with:
    python -m pc.worker
"""

from __future__ import annotations

import logging
import os
import platform
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


def collect_capabilities() -> dict[str, Any]:
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
        "machine": platform.machine(),
    }


def run_loop() -> None:
    cfg = get_settings()
    base = cfg.hub_url.rstrip("/")
    headers = {"Authorization": f"Bearer {cfg.worker_token}"}
    caps = collect_capabilities()

    log.info("Starting worker node='%s' hub='%s' work_dir='%s'", cfg.node_name, base, cfg.work_dir)

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
