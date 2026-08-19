"""
database_server.py — Specialized PostgreSQL & Project Evidence MCP Server running on Port 8103.
Implements the Model Context Protocol (MCP) Streamable HTTP + SSE transport.

Tools:
1. query_projects(sql_query, department, status, limit) - Runs real SQL queries against the projects table.
2. get_project_evidence(project_name) - Retrieves project knowledge evidence and delivery summaries.
3. list_all_projects(department, status) - Lists all projects with budgets, leads, and statuses.
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
from src.database.postgres_db import (
    execute_sql_query,
    query_projects_by_filter,
    get_project_evidence_by_name,
)

setup_logging()
logger = logging.getLogger("DatabaseMCPServer")

DATABASE_MCP_PORT = 8103
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {
    "name": "postgres-database-mcp-server",
    "version": "1.0.0",
    "description": "Specialized PostgreSQL & Project Knowledge MCP Server",
}


# ── Pydantic Input Schemas ──────────────────────────────────────────────────

class QueryProjectsInput(BaseModel):
    sql_query: Optional[str] = Field(
        None,
        description="Optional custom read-only SQL query (e.g. 'SELECT name, budget, status FROM projects WHERE department = \"Engineering\"')."
    )
    department: Optional[str] = Field(
        None,
        description="Optional department filter (e.g. 'Engineering', 'Operations', 'Security', 'AI & Data')."
    )
    status: Optional[str] = Field(
        None,
        description="Optional project status filter ('Active', 'Completed', 'In Review')."
    )
    lead_name: Optional[str] = Field(
        None,
        description="Optional lead engineer name filter (e.g. 'Vishal', 'Manoj', 'Vinod')."
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of project records to return (1-50)."
    )


class GetProjectEvidenceInput(BaseModel):
    project_name: str = Field(
        ...,
        min_length=1,
        description="Name or ID of the project to retrieve evidence for (e.g. 'Project Apollo', 'Enterprise MCP Gateway', 'Cloud Migration 2.0')."
    )


class ListAllProjectsInput(BaseModel):
    department: Optional[str] = Field(
        None,
        description="Optional department filter (e.g. 'Engineering', 'Operations')."
    )
    status: Optional[str] = Field(
        None,
        description="Optional status filter ('Active', 'Completed', 'In Review')."
    )


# ── Tool Implementations ────────────────────────────────────────────────────

async def handle_query_projects(data: QueryProjectsInput, caller: Optional[str] = None) -> dict:
    """Executes a SQL query or filtered lookup on the projects table."""
    if data.sql_query and data.sql_query.strip():
        res = execute_sql_query(data.sql_query.strip())
        res["server"] = "Postgres Database MCP Server (:8103)"
        return res

    res = query_projects_by_filter(
        department=data.department,
        status=data.status,
        lead_name=data.lead_name,
        limit=data.limit,
    )
    res["server"] = "Postgres Database MCP Server (:8103)"
    return res


async def handle_get_project_evidence(data: GetProjectEvidenceInput, caller: Optional[str] = None) -> dict:
    """Retrieves evidence summary and technical metrics for a specific project."""
    res = get_project_evidence_by_name(data.project_name)
    res["server"] = "Postgres Database MCP Server (:8103)"
    return res


async def handle_list_all_projects(data: ListAllProjectsInput, caller: Optional[str] = None) -> dict:
    """Lists all projects with high-level summaries and budgets."""
    res = query_projects_by_filter(
        department=data.department,
        status=data.status,
        limit=50,
    )
    res["server"] = "Postgres Database MCP Server (:8103)"
    return res


# ── Tool Definitions Registry ───────────────────────────────────────────────

DATABASE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "query_projects",
        "description": "Runs real SQL queries or filtered knowledge lookups against the PostgreSQL projects database table.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql_query": {
                    "type": "string",
                    "description": "Optional custom read-only SQL query (e.g. 'SELECT name, budget, status FROM projects WHERE department = \"Engineering\"').",
                },
                "department": {
                    "type": "string",
                    "description": "Filter by department (e.g. 'Engineering', 'Operations', 'Security').",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status ('Active', 'Completed', 'In Review').",
                },
                "lead_name": {
                    "type": "string",
                    "description": "Filter by project lead name.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (default: 10).",
                    "default": 10,
                },
            },
        },
        "handler": handle_query_projects,
        "model_cls": QueryProjectsInput,
    },
    {
        "name": "get_project_evidence",
        "description": "Retrieves comprehensive knowledge evidence, delivery metrics, and lead engineer info for a specified project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name or ID of the project (e.g. 'Project Apollo', 'Enterprise MCP Gateway').",
                },
            },
            "required": ["project_name"],
        },
        "handler": handle_get_project_evidence,
        "model_cls": GetProjectEvidenceInput,
    },
    {
        "name": "list_all_projects",
        "description": "Lists all enterprise projects, department assignments, budgets, and operational statuses from the database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Optional department filter.",
                },
                "status": {
                    "type": "string",
                    "description": "Optional status filter.",
                },
            },
        },
        "handler": handle_list_all_projects,
        "model_cls": ListAllProjectsInput,
    },
]


# ── Health & Readiness Probes ─────────────────────────────────────────────────

async def health_check(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "healthy",
            "server": SERVER_INFO["name"],
            "port": DATABASE_MCP_PORT,
            "tools_count": len(DATABASE_TOOLS),
            "protocol_version": MCP_PROTOCOL_VERSION,
        }
    )


# ── JSON-RPC 2.0 Request Router ───────────────────────────────────────────────

async def handle_jsonrpc_request(payload: Dict[str, Any], caller: str) -> Dict[str, Any]:
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if not method:
        return make_jsonrpc_error(
            code=JSONRPCErrorCodes.INVALID_REQUEST,
            message="Invalid Request: 'method' is required.",
            req_id=req_id,
        )

    # 1. initialize
    if method == "initialize":
        return make_jsonrpc_success(
            result={
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "logging": {},
                },
                "serverInfo": SERVER_INFO,
            },
            req_id=req_id,
        )

    # 2. notifications/initialized
    if method == "notifications/initialized":
        return make_jsonrpc_success(result={}, req_id=req_id)

    # 3. ping
    if method == "ping":
        return make_jsonrpc_success(result={}, req_id=req_id)

    # 4. tools/list
    if method == "tools/list":
        tools_manifest = [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in DATABASE_TOOLS
        ]
        return make_jsonrpc_success(result={"tools": tools_manifest}, req_id=req_id)

    # 5. tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}

        if not tool_name:
            return make_jsonrpc_error(
                code=JSONRPCErrorCodes.INVALID_PARAMS,
                message="Invalid params: 'name' is required for tools/call.",
                req_id=req_id,
            )

        for tool in DATABASE_TOOLS:
            if tool["name"] == tool_name:
                try:
                    model_cls = tool["model_cls"]
                    handler = tool["handler"]
                    validated_input = model_cls(**arguments)
                    result = await handler(validated_input, caller=caller)
                    is_error = result.get("status") == "failed"
                    return make_jsonrpc_success(
                        result={
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2),
                                }
                            ],
                            "isError": is_error,
                        },
                        req_id=req_id,
                    )
                except Exception as exc:
                    return make_jsonrpc_error(
                        code=JSONRPCErrorCodes.INTERNAL_ERROR,
                        message=str(exc),
                        req_id=req_id,
                    )

        return make_jsonrpc_error(
            code=JSONRPCErrorCodes.METHOD_NOT_FOUND,
            message=f"Tool '{tool_name}' not found on Database MCP Server.",
            req_id=req_id,
        )

    return make_jsonrpc_error(
        code=JSONRPCErrorCodes.METHOD_NOT_FOUND,
        message=f"Method '{method}' not found.",
        req_id=req_id,
    )


# ── Starlette HTTP & SSE Endpoints ──────────────────────────────────────────

async def mcp_post_endpoint(request: Request) -> JSONResponse:
    caller = getattr(request.state, "caller_identity", "anonymous_caller")
    session = getattr(request.state, "session", None)
    try:
        body = await request.body()
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return JSONResponse(
            make_jsonrpc_error(code=JSONRPCErrorCodes.PARSE_ERROR, message="Parse error: Invalid JSON payload."),
            status_code=400,
        )

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
        endpoint_uri = f"http://localhost:{DATABASE_MCP_PORT}/mcp?session_id={session_id}"
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
    uvicorn.run(app, host="0.0.0.0", port=DATABASE_MCP_PORT, log_level="info")
