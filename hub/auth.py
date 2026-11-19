"""Constant-time token authentication for AI clients and compute workers."""

from __future__ import annotations

import hmac
from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from hub.config import get_settings


def extract_token(request: Request) -> str:
    """Extract bearer token, X-API-Key header, or ?token= query param for /dashboard."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    header_key = request.headers.get("x-api-key", "").strip()
    if header_key:
        return header_key
    if request.url.path == "/dashboard":
        return request.query_params.get("token", "").strip()
    return ""


def token_matches(candidate: str, allowed: Iterable[str]) -> bool:
    """Compare candidate token against allowed non-empty secrets in constant time."""
    if not candidate:
        return False
    return any(
        secret and hmac.compare_digest(candidate, secret)
        for secret in allowed
    )


class TokenMiddleware(BaseHTTPMiddleware):
    """Protect /mcp and /api routes while keeping /health public."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in ("/health", "/"):
            return await call_next(request)

        settings = get_settings()
        token = extract_token(request)

        # Worker endpoints accept either WORKER_TOKEN or HUB_TOKEN
        if path.startswith("/api/jobs") or path.startswith("/api/nodes") or path.startswith("/api/files"):
            allowed = (settings.worker_token, settings.hub_token)
        else:
            # MCP & management routes require HUB_TOKEN
            allowed = (settings.hub_token,)

        if not token_matches(token, allowed):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: invalid or missing API token."},
            )

        return await call_next(request)
