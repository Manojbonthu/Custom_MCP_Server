"""
template_server.py — Reusable Boilerplate Template for Creating New MCP Microservice Servers.

How to use this template:
1. Copy this file to a new file in `src/servers/` (e.g. `src/servers/weather_server.py` or `src/servers/database_server.py`).
2. Update `SERVER_PORT` and `SERVER_INFO`.
3. Add your custom tools following the 3-step pattern below (Pydantic Schema -> Handler Function -> Tools List).
4. Add the server to `run_servers.py` and `ui/index.html`.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional
import uvicorn

from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from src.auth.middleware import AuthMiddleware
from src.auth.session_manager import session_manager
from src.common.errors import JSONRPCErrorCodes, make_jsonrpc_error, make_jsonrpc_success
from src.common.logging import setup_logging

setup_logging()
logger = logging.getLogger("TemplateMCPServer")

# ── 1. Configure Server Identity & Port ──────────────────────────────────────
SERVER_PORT = 8104  # Choose an available port (e.g., 8104, 8105, etc.)
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "custom-mcp-server-template",
    "version": "1.0.0",
    "description": "Custom Modular MCP Microservice Server",
}


# ── 2. Define Pydantic Input Schemas for Your Tools ──────────────────────────

class SampleActionInput(BaseModel):
    name: str = Field(..., description="Name of the entity to process.")
    count: int = Field(1, ge=1, le=100, description="Number of items to generate (1-100).")


# ── 3. Define Async Tool Handlers ────────────────────────────────────────────

async def handle_sample_action(data: SampleActionInput, caller: Optional[str] = None) -> dict:
    """
    Executes your custom business logic.
    Returns standard JSON dictionary results.
    """
    return {
        "status": "success",
        "processed_name": data.name,
        "count": data.count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "server": f"{SERVER_INFO['name']} (:{SERVER_PORT})",
        "message": f"Processed '{data.name}' with count {data.count} successfully.",
    }


# ── 4. Register Tools in the Manifest ────────────────────────────────────────
# To ADD a tool: Append an entry here.
# To REMOVE a tool: Comment out or delete its entry here.

CUSTOM_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "sample_action",
        "description": "Performs a sample customizable action on the MCP Server.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the entity to process."},
                "count": {"type": "integer", "description": "Number of items to generate (1-100).", "default": 1},
            },
            "required": ["name"],
        },
        "handler": handle_sample_action,
        "model_cls": SampleActionInput,
    },
]


# ── 5. Standard MCP Protocol Endpoints (Zero Boilerplate Needed) ─────────────

async def health_check(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "healthy",
            "server": SERVER_INFO["name"],
            "port": SERVER_PORT,
            "tools_count": len(CUSTOM_TOOLS),
            "protocol_version": MCP_PROTOCOL_VERSION,
        }
    )


async def handle_jsonrpc_request(payload: Dict[str, Any], caller: str) -> Dict[str, Any]:
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if not method:
        return make_jsonrpc_error(JSONRPCErrorCodes.INVALID_REQUEST, "Missing 'method' field.", req_id)

    if method == "initialize":
        return make_jsonrpc_success(
            result={
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}, "logging": {}},
                "serverInfo": SERVER_INFO,
            },
            req_id=req_id,
        )

    if method == "notifications/initialized":
        return make_jsonrpc_success(result={}, req_id=req_id)

    if method == "ping":
        return make_jsonrpc_success(result={}, req_id=req_id)

    # Return registered tools
    if method == "tools/list":
        tools_manifest = [
            {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
            for t in CUSTOM_TOOLS
        ]
        return make_jsonrpc_success(result={"tools": tools_manifest}, req_id=req_id)

    # Execute tool by name
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}

        for tool in CUSTOM_TOOLS:
            if tool["name"] == tool_name:
                try:
                    validated_input = tool["model_cls"](**arguments)
                    result = await tool["handler"](validated_input, caller=caller)
                    is_error = result.get("status") == "failed"
                    return make_jsonrpc_success(
                        result={
                            "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                            "isError": is_error,
                        },
                        req_id=req_id,
                    )
                except Exception as exc:
                    return make_jsonrpc_error(JSONRPCErrorCodes.INTERNAL_ERROR, str(exc), req_id)

        return make_jsonrpc_error(JSONRPCErrorCodes.METHOD_NOT_FOUND, f"Tool '{tool_name}' not found.", req_id)

    return make_jsonrpc_error(JSONRPCErrorCodes.METHOD_NOT_FOUND, f"Method '{method}' not found.", req_id)


async def mcp_post_endpoint(request: Request) -> JSONResponse:
    caller = getattr(request.state, "caller_identity", "anonymous_caller")
    session = getattr(request.state, "session", None)
    try:
        body = await request.body()
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return JSONResponse(make_jsonrpc_error(JSONRPCErrorCodes.PARSE_ERROR, "Invalid JSON payload."), status_code=400)

    if isinstance(payload, list):
        results = await asyncio.gather(*[handle_jsonrpc_request(req, caller) for req in payload])
        if session:
            session.add_event(event_name="message", data=json.dumps(results))
        return JSONResponse(results, status_code=200)

    result = await handle_jsonrpc_request(payload, caller)
    if session:
        session.add_event(event_name="message", data=json.dumps(result))
    return JSONResponse(result, status_code=200)


async def mcp_sse_endpoint(request: Request) -> StreamingResponse:
    session = getattr(request.state, "session", None)
    session_id = getattr(request.state, "session_id", "default")
    caller = getattr(request.state, "caller_identity", "unknown")

    async def sse_generator() -> AsyncGenerator[str, None]:
        endpoint_uri = f"http://localhost:{SERVER_PORT}/mcp?session_id={session_id}"
        yield f"event: endpoint\ndata: {endpoint_uri}\n\n"
        try:
            while True:
                if session:
                    try:
                        event = await asyncio.wait_for(session.queue.get(), timeout=15.0)
                        yield f"id: {event.event_id}\nevent: {event.event_name}\ndata: {event.data}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
                else:
                    await asyncio.sleep(15.0)
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


# ── Starlette ASGI Application ──────────────────────────────────────────────
routes = [
    Route("/health", endpoint=health_check, methods=["GET"]),
    Route("/mcp", endpoint=mcp_post_endpoint, methods=["POST"]),
    Route("/mcp", endpoint=mcp_sse_endpoint, methods=["GET"]),
    Route("/sse", endpoint=mcp_sse_endpoint, methods=["GET"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    ),
    Middleware(AuthMiddleware),
]

app = Starlette(routes=routes, middleware=middleware)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_level="info")
