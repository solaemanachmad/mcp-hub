"""Built-in Autonomous Research & Experiment Agent running inside MCP Hub."""

from __future__ import annotations

import json
from typing import Any

from hub.db import db
from hub.services import exp as exp_svc
from hub.services import memory as mem_svc
from hub.services import papers as paper_svc
from hub.services import rag as rag_svc
from hub.services.ai import ai_client


async def run_research_agent(
    project: str,
    goal: str,
    search_query: str = "",
    provider: str = "",
    save_to_notes: bool = True,
) -> dict[str, Any]:
    """Execute an autonomous multi-step research & synthesis cycle on Oracle Cloud.

    Steps executed automatically:
    1. Load existing project context (notes, paper count, recent experiments).
    2. Search the internal pgvector knowledge base for relevant ingested excerpts.
    3. Search external academic databases (Semantic Scholar & arXiv) if search_query is given.
    4. Rank existing project experiments to include quantitative progress.
    5. Synthesize a structured report & action plan using the selected LLM provider.
    6. Persist the agent's report into shared project notes for all other AI clients.
    """
    steps: list[str] = []

    context = await mem_svc.get_context(project=project, limit=5)
    steps.append(f"Loaded context for project '{context['project']}'")

    query = (search_query or goal)[:120]
    kb_hits = await rag_svc.search_kb(project=project, query=query, top_k=4)
    steps.append(f"Searched internal knowledge base: {kb_hits['count']} chunk(s)")

    external_papers: list[dict[str, Any]] = []
    if search_query:
        ext = await paper_svc.search_papers(query=search_query, limit=4)
        external_papers = ext.get("papers", [])
        steps.append(f"Fetched {len(external_papers)} external paper(s) for '{search_query}'")

    exp_ranking = await exp_svc.compare_experiments(project=project, metric="f1", limit=5)
    steps.append(f"Compared {exp_ranking['count']} project experiment(s)")

    prompt = (
        f"Project: {context['project']} ({context['name']})\n"
        f"Goal: {goal}\n\n"
        f"--- Existing Project Context ---\n{json.dumps(context, default=str)[:3500]}\n\n"
        f"--- Internal Knowledge Base Hits ---\n{json.dumps(kb_hits['hits'], default=str)[:3500]}\n\n"
        f"--- External Papers Found ---\n{json.dumps(external_papers, default=str)[:3500]}\n\n"
        f"--- Top Experiments ---\n{json.dumps(exp_ranking['experiments'], default=str)[:2000]}\n\n"
        "Produce a concise, actionable report with:\n"
        "1. Key Findings & Synthesis\n"
        "2. Research Gaps or Experiment Insights\n"
        "3. Concrete Next Steps"
    )

    llm_res = await ai_client.chat(
        prompt=prompt,
        system="You are an autonomous PhD-level AI research and ML engineering agent.",
        provider=provider,
    )
    report = llm_res["reply"]
    steps.append(f"Synthesized report via {llm_res['provider']} ({llm_res['model']})")

    note_id = None
    if save_to_notes and report:
        saved = await db.save_note(
            project_slug=project,
            title=f"Agent Report: {goal[:60]}",
            content=report,
            author_ai=f"hub-agent/{llm_res['provider']}",
            tags=["agent", llm_res["provider"]],
        )
        note_id = saved["id"]
        steps.append(f"Saved report to shared project notes (id={note_id})")

    return {
        "project": context["project"],
        "goal": goal,
        "provider": llm_res["provider"],
        "model": llm_res["model"],
        "steps": steps,
        "note_id": note_id,
        "report": report,
    }
