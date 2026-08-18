"""
server.py — notifications-mcp server entrypoint.

Wires together:
  1. MCP server (MCPServer / FastMCP with Streamable HTTP)
  2. Gmail OAuth routes (/auth/gmail/start, /auth/gmail/callback)
  3. Channel tool registry (reads enabled_channels from config.yaml)

MCP endpoint: http://localhost:8100/mcp
OAuth start:  http://localhost:8100/auth/gmail/start

IMPORTANT: This file NEVER imports channel-specific code directly.
It only calls registry.register_all(mcp). That contract is what
allows new channels to be added without ever touching this file.

Run with:
  python -m src.server
  # or after pip install -e .:
  notifications-mcp
"""

import logging

import uvicorn
from mcp.server.mcpserver.server import MCPServer
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from src.channels.mail.auth import gmail_oauth_callback, gmail_oauth_start
from src.common.logging import setup_logging
from src.config import load_config
from src.registry import register_all

# ── Logging must be set up before anything else logs ─────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ── MCP Server ────────────────────────────────────────────────────────────────
# FastMCP is the stable high-level API in mcp >= 2.0.0
mcp = MCPServer("notifications-mcp")

# Register tools for all channels listed in config.yaml
register_all(mcp)

# Get the ASGI-compatible Starlette app for Streamable HTTP transport
# IMPORTANT: pass mcp_app.lifespan to the parent Starlette app —
# without this you get "Task group not initialized" errors at runtime.
mcp_app = mcp.streamable_http_app()


from starlette.responses import JSONResponse
from pathlib import Path

# ── Health & Readiness Probes ─────────────────────────────────────────────────
async def health_check(request) -> JSONResponse:
    """Liveness probe: verifies the HTTP server is running."""
    return JSONResponse({"status": "healthy", "service": "notifications-mcp"})


async def readiness_check(request) -> JSONResponse:
    """Readiness probe: verifies configured channels and token readiness."""
    cfg = load_config()
    mail_cfg = cfg.channels.get("mail")
    token_ready = Path(mail_cfg.token_path).exists() if mail_cfg else False
    return JSONResponse(
        {
            "status": "ready" if token_ready else "needs_auth",
            "channels": {
                "mail": "configured" if token_ready else "unauthenticated"
            },
        },
        status_code=200 if token_ready else 503,
    )


# ── Full ASGI app (MCP + OAuth routes + Health Probes) ───────────────────────
app = Starlette(
    routes=[
        # Probes
        Route("/health",              endpoint=health_check),
        Route("/ready",               endpoint=readiness_check),
        # Gmail OAuth flow endpoints
        Route("/auth/gmail/start",    endpoint=gmail_oauth_start),
        Route("/auth/gmail/callback", endpoint=gmail_oauth_callback),
        # MCP Streamable HTTP endpoint — all MCP clients connect here
        Mount("/mcp", app=mcp_app),
    ],
    lifespan=mcp_app.router.lifespan_context,
)


# ── Entrypoint ────────────────────────────────────────────────────────────────
def main() -> None:
    cfg = load_config()
    logger.info(
        f"Starting notifications-mcp | "
        f"host={cfg.server.host} | port={cfg.server.port}"
    )
    logger.info(f"MCP endpoint  → http://localhost:{cfg.server.port}/mcp")
    logger.info(f"Gmail OAuth   → http://localhost:{cfg.server.port}/auth/gmail/start")

    uvicorn.run(
        "src.server:app",
        host=cfg.server.host,
        port=cfg.server.port,
        reload=False,
        log_config=None,  # Disable uvicorn's default logging — we use our JSON logger
    )


if __name__ == "__main__":
    main()
