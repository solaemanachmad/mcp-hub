"""Zero-build lightweight HTML status dashboard served at GET /dashboard."""

from __future__ import annotations

import html
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from hub.db import db
from hub.server import LOADED_PLUGINS

router = APIRouter(tags=["dashboard"])


def _esc(val: Any) -> str:
    return html.escape(str(val if val is not None else ""))


@router.get("/dashboard", response_class=HTMLResponse)
async def render_dashboard() -> HTMLResponse:
    """Render a single-page read-only overview of nodes, projects, datasets, experiments, and notes."""
    projects = await db.list_projects()
    nodes = await db.list_nodes()
    datasets = await db.list_datasets()
    exps = await db.list_experiments("all", limit=15)
    papers = await db.list_papers("all", limit=10)
    plugins = LOADED_PLUGINS

    node_rows = "".join(
        f"<tr><td><b>{_esc(n['name'])}</b></td><td>{_esc(n['kind'])}</td>"
        f"<td><span class='badge {_esc(n['status'])}'>{_esc(n['status'])}</span></td>"
        f"<td><code>{_esc(n.get('capabilities', {}))}</code></td></tr>"
        for n in nodes
    ) or "<tr><td colspan='4'>No worker heartbeats yet</td></tr>"

    proj_rows = "".join(
        f"<tr><td><code>{_esc(p['slug'])}</code></td><td>{_esc(p['name'])}</td>"
        f"<td>{_esc(p['category'])}</td><td><span class='badge {_esc(p['status'])}'>{_esc(p['status'])}</span></td>"
        f"<td>{p['paper_count']}</td><td>{p['dataset_count']}</td><td>{p['exp_count']}</td><td>{p['note_count']}</td></tr>"
        for p in projects
    )

    ds_rows = "".join(
        f"<tr><td><code>{_esc(d['slug'])}</code></td><td>{_esc(d['project_slug'])}</td>"
        f"<td><span class='badge'>{_esc(d['location'])}</span></td>"
        f"<td><code>{_esc(d['kaggle_ref'] or d['mount_path'])}</code></td>"
        f"<td>{_esc(d['format'])}</td><td>{_esc(d['num_samples'])}</td></tr>"
        for d in datasets
    ) or "<tr><td colspan='6'>No datasets registered yet</td></tr>"

    exp_rows = "".join(
        f"<tr><td><code>{_esc(e['id'])}</code></td><td>{_esc(e['project_slug'])}</td>"
        f"<td>{_esc(e['name'])}</td><td>{_esc(e['target_node'])}</td>"
        f"<td><code>{_esc(e.get('dataset_slug') or '-')}</code></td>"
        f"<td><span class='badge {_esc(e['status'])}'>{_esc(e['status'])}</span></td>"
        f"<td><code>{_esc(e.get('metrics', {}))}</code></td></tr>"
        for e in exps
    ) or "<tr><td colspan='7'>No experiments queued yet</td></tr>"

    paper_rows = "".join(
        f"<tr><td>{p['id']}</td><td><code>{_esc(p['project_slug'])}</code></td>"
        f"<td>{_esc(p['title'])} ({_esc(p.get('year') or 'n.d.')})</td>"
        f"<td>{_esc(p.get('method') or '-')}</td><td>{_esc(p.get('dataset_used') or '-')}</td>"
        f"<td>{_esc(p.get('key_metrics') or '-')}</td></tr>"
        for p in papers
    ) or "<tr><td colspan='6'>No papers ingested yet</td></tr>"

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCP Hub Dashboard</title>
<style>
  :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --muted: #94a3b8; --accent: #38bdf8; --border: #334155; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; }}
  h1, h2 {{ margin-top: 0; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; margin-bottom: 20px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 16px; overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; }}
  code {{ background: #0b1120; padding: 2px 6px; border-radius: 4px; color: var(--accent); font-size: 12px; }}
  .badge {{ padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; background: #334155; }}
  .online, .active, .completed {{ background: #065f46; color: #6ee7b7; }}
  .queued, .running {{ background: #1e3a8a; color: #93c5fd; }}
  .offline, .failed, .archived {{ background: #7f1d1d; color: #fca5a5; }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <h1>MCP Hub — Research & Compute Overview</h1>
      <div style="color: var(--muted); font-size: 13px;">Loaded plugin modules: <code>{", ".join(plugins)}</code></div>
    </div>
  </div>

  <div class="card">
    <h2>Compute Nodes (Tailscale & Kaggle)</h2>
    <table>
      <thead><tr><th>Node</th><th>Kind</th><th>Status</th><th>Capabilities</th></tr></thead>
      <tbody>{node_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Projects by Category</h2>
    <table>
      <thead><tr><th>Slug</th><th>Name</th><th>Category</th><th>Status</th><th>Papers</th><th>Datasets</th><th>Experiments</th><th>Notes</th></tr></thead>
      <tbody>{proj_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Dataset Registry (Kaggle / PC / Mac)</h2>
    <table>
      <thead><tr><th>Slug</th><th>Project</th><th>Location</th><th>Kaggle Ref / Mount Path</th><th>Format</th><th>Samples</th></tr></thead>
      <tbody>{ds_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Recent Experiments</h2>
    <table>
      <thead><tr><th>ID</th><th>Project</th><th>Name</th><th>Node</th><th>Dataset</th><th>Status</th><th>Metrics</th></tr></thead>
      <tbody>{exp_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Recent Papers & Review Matrix</h2>
    <table>
      <thead><tr><th>ID</th><th>Project</th><th>Title (Year)</th><th>Method</th><th>Dataset</th><th>Key Metrics</th></tr></thead>
      <tbody>{paper_rows}</tbody>
    </table>
  </div>
</body>
</html>"""
    return HTMLResponse(content=page)
