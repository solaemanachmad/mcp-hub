"""Autonomous Research & Experiment Agent MCP tool."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from hub.services import agent as agent_svc


def register(mcp: FastMCP) -> None:
    """Attach the built-in autonomous agent tool to FastMCP."""

    @mcp.tool()
    async def run_agent(
        project: str,
        goal: str,
        search_query: str = "",
        provider: str = "",
        save_to_notes: bool = True,
    ) -> dict[str, Any]:
        """Run the built-in autonomous agent on Oracle Cloud to gather context, search papers/RAG, analyze experiments, and save a report.

        Args:
            project: Project slug (e.g. 'eye_movement').
            goal: High-level objective for the agent to execute.
            search_query: Optional academic search query to pull fresh papers from Semantic Scholar/arXiv.
            provider: LLM provider to power the agent ('qwen', 'deepseek', 'baidu', 'weixin', 'gemini', 'openai').
            save_to_notes: Automatically save the agent's final report to shared project memory.
        """
        return await agent_svc.run_research_agent(
            project=project,
            goal=goal,
            search_query=search_query,
            provider=provider,
            save_to_notes=save_to_notes,
        )
