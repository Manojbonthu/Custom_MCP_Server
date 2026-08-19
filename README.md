# Streamable HTTP + SSE MCP Server (Multi-Agent AI Orchestrator)

> **Production-Ready Configuration-Driven Model Context Protocol (MCP) Orchestrator** 
> Features **Streamable HTTP + SSE**, **Bearer Token Authentication**, **Strict Session-Identity Binding**, **RBAC Security Layers**, and a fully autonomous **Groq-powered Multi-Agent Backend Planner**.

---

## 🌟 Core Architecture & Standards

1. **Official MCP Specification Standard**: JSON-RPC 2.0 transport over Streamable HTTP (`POST /mcp` and `GET /mcp` SSE).
2. **Autonomous Multi-Agent Backend (`AgentRuntime`)**:
   - Web application transmits high-level natural language requests securely through `agent_request`.
   - The backend directly natively plans, executes, and evaluates contextually aware steps via Groq (`qwen/qwen3.6-27b`).
3. **Configuration-Driven Security**:
   - `agents.yaml`: Dynamically maps external tokens to backend User Identities.
   - `roles.yaml`: Defines RBAC levels restricting what tools and specific data sources a role can process.
   - `servers.yaml`: Connects to multiple disparate MCP remote servers transparently.
   - `orchestration.yaml`: Resolves user capability intent safely to underlying physical resources (Fallback routing).
4. **Security Guardrails**:
   - **Identity-First Auth**: The `IdentityService` explicitly ties every payload to pre-configured profiles mapping roles.
   - **Policy Engine**: High-level execution approval enforcing intersection of "Role Allowed" vs "Agent Allowed".
   - **Full Audit Trace**: Every network action creates an unbreakable SHA-256 chained transaction within the persistent `audit.db` SQLite core.
5. **Human Approval Gateway**: 
   - Destructive operations automatically stall the Agent Backend until human override authorization is submitted via the UI.

---

## 📁 Repository Structure

```
Custom_MCP_Server/
├── agents.yaml                    # Agent ID & Auth mapping profiles
├── roles.yaml                     # RBAC permissions per class ceiling
├── servers.yaml                   # Remote server integrations
├── orchestration.yaml             # Fallback route mapping matrix
├── pyproject.toml                 # Package definition & dependencies
├── requirements.txt               # Dependencies
├── .env                           # Local machine environment variables (API keys/Tokens)
├── src/
│   ├── server.py                  # Uvicorn Lifespan & JSON-RPC entrypoint Router
│   ├── config_schema_loader.py    # Strict YAML configuration parser
│   ├── registry.py                # Local + Remote dynamic tool registries
│   ├── agent/             
│   │   ├── runtime.py             # Agent execution engine
│   │   ├── planner.py             # Groq natural language task extrapolater
│   │   ├── decision.py            # Realtime Tool Discovery engine
│   │   ├── execution.py           # Tool bridging context interface
│   │   └── state.py               # Workflow tracker
│   ├── auth/                      # Session Context verification headers
│   ├── security/
│   │   ├── policy_engine.py       # RBAC compliance intersection resolver
│   │   ├── identity_service.py    # Bearer verification mechanism
│   │   └── audit.py               # SQLite persisted hashing chain 
│   ├── orchestration/
│   │   ├── resolver.py            # Physical implementation router
│   └── tools/
│       ├── datetime_tool.py       # get_current_datetime implementation
│       └── email_tool.py          # send_email SMTP logic
└── ui/
    └── index.html                 # The Single Page Application (UI React layer built via raw JS)
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- A `.env` file in the root containing your `GROQ_API_KEY` and specific user tokens (`VISHAL_TEST_TOKEN`, `VINOD_TEST_TOKEN`).

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Server
```bash
python -m src.server
```

You will see:
```log
{"timestamp": "...", "level": "INFO", "message": "Starting Streamable MCP Server | host=0.0.0.0 | port=8100"}
{"timestamp": "...", "level": "INFO", "message": "MCP POST/GET endpoint  → http://localhost:8100/mcp"}
{"timestamp": "...", "level": "INFO", "message": "Health check probe     → http://localhost:8100/health"}
```

Open a web browser directly to: **http://localhost:8100/**

You can uniquely login as users (e.g. `vinod123` or `vishal123`) from the `ui/index.html` interface to authenticate and see restricted execution environments.

---

## 🔌 Connecting with MCP Inspector & cURL

### Connect via MCP Inspector:
```bash
npx @modelcontextprotocol/inspector
```
Connect to URL: `http://localhost:8100/mcp` with Custom Header: `Authorization: Bearer <your-env-token>`

### Sample cURL Invocation (Direct JSON-RPC bypass to tool):
```bash
curl -X POST http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-env-token>" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_current_datetime",
      "arguments": {"timezone": "Asia/Kolkata"}
    }
  }'
```

---

## 🛡️ Tamper-Evident Audit Database Storage
All user authentication mappings, decision contexts, tool interactions, and error thresholds globally execute persistently within local `audit.db` using SHA-256 rolling chain hashes, preventing retro-active metadata modification from potentially rogue AI agents.
