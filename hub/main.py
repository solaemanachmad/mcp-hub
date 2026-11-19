"""Combined ASGI application serving MCP (/mcp), Orchestrator API (/api), and /health."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from hub.api import router as api_router
from hub.auth import TokenMiddleware
from hub.db import db
from hub.server import mcp
from hub.ui import router as ui_router

# Initialize streamable HTTP sub-app before lifespan starts
mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await db.connect()
    async with mcp.session_manager.run():
        yield
    await db.close()


def create_app() -> FastAPI:
    application = FastAPI(
        title="MCP Hub",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(TokenMiddleware)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "mcp-hub"}

    application.include_router(api_router)
    application.include_router(ui_router)
    application.mount("/", mcp_app)
    return application


app = create_app()
