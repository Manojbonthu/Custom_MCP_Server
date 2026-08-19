"""
registry.py — Tool registration for MCP server.
Registers get_current_datetime and send_email tools with schemas and handlers.
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from src.tools.datetime_tool import (
    GetCurrentDateTimeInput,
    get_current_datetime_handler,
)
from src.tools.email_tool import (
    SendEmailInput,
    send_email_handler,
)

logger = logging.getLogger(__name__)

# Registry of MCP Tools metadata and handlers
TOOL_DEFINITIONS = [
    {
        "name": "get_current_datetime",
        "description": "Returns the current host system date and time with optional IANA timezone conversion (e.g. 'UTC', 'America/New_York', 'Asia/Kolkata').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "Optional IANA timezone name (e.g. 'UTC', 'America/New_York', 'Asia/Kolkata', 'Europe/London'). Defaults to system local time if omitted.",
                }
            },
            "required": [],
        },
        "model_cls": GetCurrentDateTimeInput,
        "handler": get_current_datetime_handler,
    },
    {
        "name": "send_email",
        "description": "Sends an email notification via server SMTP with strict security guardrails (recipient allowlist checking, per-caller rate limits, and prompt injection defense).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address (e.g. 'ops@company.com', 'manager@company.com'). Must be in the authorized allowlist.",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject line of the email. Must not contain prompt injection sequences.",
                },
                "body": {
                    "type": "string",
                    "description": "Body content of the email. Must not contain prompt injection sequences.",
                },
            },
            "required": ["to", "subject", "body"],
        },
        "model_cls": SendEmailInput,
        "handler": send_email_handler,
    },
]


class ToolRegistry:
    def __init__(self):
        # Tools dynamically registered or initially built-in.
        self.tool_definitions: List[Dict[str, Any]] = [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
                "_local_handler": t["handler"],
                "_model_cls": t["model_cls"],
                "_is_local": True
            }
            for t in TOOL_DEFINITIONS
        ]
        self._server_registry = None

    def set_server_registry(self, registry):
        self._server_registry = registry

    def register_remote_tools(self, server_name: str, tools: List[Dict[str, Any]]):
        """Registers a list of tools dynamically discovered from a remote server."""
        for tool in tools:
            # We add metadata identifying its remote server source
            tool["_is_local"] = False
            tool["_remote_server"] = server_name
            self.tool_definitions.append(tool)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns standard tool manifests for MCP tools/list requests."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in self.tool_definitions
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], caller: Optional[str] = None) -> dict:
        """Executes the requested tool by name, locally or remotely."""
        for tool_meta in self.tool_definitions:
            if tool_meta["name"] == tool_name:
                if tool_meta.get("_is_local"):
                    # Local execution
                    model_cls = tool_meta["_model_cls"]
                    handler = tool_meta["_local_handler"]
                    validated_input = model_cls(**(arguments or {}))
                    return await handler(validated_input, caller=caller)
                else:
                    # Remote execution
                    server_name = tool_meta.get("_remote_server")
                    if self._server_registry:
                        client = self._server_registry.get_client(server_name)
                        if client:
                            logger.info(f"Proxying tool {tool_name} to server {server_name}")
                            return await client.call_tool(tool_name, arguments)
                        else:
                            raise RuntimeError(f"Client for server '{server_name}' not found.")
                    else:
                        raise RuntimeError(f"ServerRegistry not initialized for remote tool execution.")

        raise KeyError(f"Tool '{tool_name}' not found.")

global_tool_registry = ToolRegistry()

def get_tool_definitions() -> List[Dict[str, Any]]:
    return global_tool_registry.get_tool_definitions()

async def execute_tool(tool_name: str, arguments: Dict[str, Any], caller: Optional[str] = None) -> dict:
    return await global_tool_registry.execute_tool(tool_name, arguments, caller=caller)



def register_all(mcp_server: Any) -> None:
    """
    If using FastMCP or MCPServer instance, registers all tools directly.
    """
    if hasattr(mcp_server, "tool"):
        @mcp_server.tool(name="get_current_datetime", description="Returns host system date and time with optional IANA timezone conversion.")
        async def get_current_datetime(timezone: Optional[str] = None) -> dict:
            return await get_current_datetime_handler(GetCurrentDateTimeInput(timezone=timezone))

        @mcp_server.tool(name="send_email", description="Sends an email notification via server SMTP with strict security guardrails.")
        async def send_email(to: str, subject: str, body: str) -> dict:
            return await send_email_handler(SendEmailInput(to=to, subject=subject, body=body))

        logger.info("Registered tools with MCP Server instance.")
