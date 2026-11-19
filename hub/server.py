"""Unified FastMCP server with automatic plugin discovery for hub/tools/*.py."""

from __future__ import annotations

import importlib
import pkgutil

from mcp.server.fastmcp import FastMCP

import hub.tools


def load_plugins(mcp: FastMCP) -> list[str]:
    """Auto-discover and register every tool/prompt module inside hub/tools/."""
    loaded: list[str] = []
    for module_info in sorted(pkgutil.iter_modules(hub.tools.__path__), key=lambda m: m.name):
        if module_info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"hub.tools.{module_info.name}")
        register_fn = getattr(mod, "register", None)
        if callable(register_fn):
            register_fn(mcp)
            loaded.append(module_info.name)
    return loaded


LOADED_PLUGINS: list[str] = []


def build_mcp() -> FastMCP:
    """Create and configure the unified stateless Streamable HTTP MCP server."""
    mcp = FastMCP(
        name="mcp-hub",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/mcp",
    )
    LOADED_PLUGINS.clear()
    LOADED_PLUGINS.extend(load_plugins(mcp))
    return mcp


mcp = build_mcp()
