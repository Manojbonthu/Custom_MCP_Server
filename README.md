# Multi-Agent MCP Zero-Trust Architecture & AI Gateway

## 1. PROJECT OVERVIEW
**What this MCP platform does:** This is a comprehensive, multi-server Model Context Protocol (MCP) ecosystem. It orchestrates user requests across an AI Gateway, delegating tasks to autonomous agent runtimes and specialized microservers (Gmail, Time).

**Main purpose:** To securely expose tools via standard JSON-RPC 2.0 protocol over HTTP/SSE streams to Large Language Models (Groq, Gemini).

**Problem it solves:** Prevents unauthorized LLM tool execution, solves the "secret zero" problem using HashiCorp OpenBao, and standardizes multi-agent tool routing without exposing infrastructure credentials to the AI.

**Major capabilities (CURRENT):** 
- Cryptographic JWT Bearer Token authentication.
- Centralized Policy Engine (RBAC).
- JIT (Just-in-Time) authorization evaluation.
- Hub-and-Spoke tool orchestration over HTTP.
- Cross-server request proxying `ServerRegistry`.
- Dynamic credential resolution via HashiCorp OpenBao (Vault).

## 2. CURRENT ARCHITECTURE
**Complete Current Flow:**
1. **User** logs into the UI.
2. **JWT Authentication**: `AuthMiddleware` verifies the JSON Web Token.
3. **IdentityService**: Resolves the JWT `sub` exactly to an agent ID and Role in `agents.yaml`.
4. **MCP Session**: Maps the identity securely to a streaming `SessionManager`.
5. **Orchestrator/AgentRuntime**: Groq LLM evaluates the user prompt, formulating a plan with selected tools.
6. **PolicyEngine**: Authorizes the execution of the selected tool against the user's role.
7. **ServerRegistry/ExecutionEngine**: Proxies the JSON-RPC call from Port 8100 down to the specific microservice (e.g., Gmail on 8101).
8. **MCP Tool Server**: Receives the request and executes the physical tool.
9. **CredentialService**: Identifies that it needs an SMTP password.
10. **OpenBao**: Authenticates via AppRole and returns the password to Python RAM.
11. **External Service**: The execution communicates with Google (IMAP/SMTP) dynamically and destroys the credential.

## 3. CURRENT SECURITY MODEL
- **JWT authentication (CURRENT):** `jwt_validator.py` evaluates token signatures mathematically before processing requests.
- **Identity resolution (CURRENT):** Extracts identity from `sub` and links to `agents.yaml`.
- **Session identity binding (CURRENT):** SSE sessions securely pin the UUID to the resolved caller identity.
- **PolicyEngine authorization (CURRENT):** Evaluates `roles.yaml` ceilings and local agent blocklists.
- **Agent/tool authorization (CURRENT):** Validated before tool execution.
- **Session authorization cache (CURRENT):** `tools/call` utilizes `session.cached_permissions` with a 300s TTL.
- **JIT authorization (CURRENT):** `AgentRuntime` calculates tool allowances immediately before dynamic tool triggers (though it bypasses the session cache currently).
- **Origin validation & Session protection (CURRENT):** Handled by CORS policies and strict SSE token validation.
- **Error sanitization (CURRENT):** Avoids leaking stack traces in output.
- **Audit events & Correlation IDs (CURRENT):** Hashes and writes events synchronously, passing `correlation_id` across servers.
- **Credential protection (CURRENT):** Does not write fetched credentials to disk.

*(Note: Authentication verifies WHO you are. Authorization verifies WHAT you can do. These are strictly separated in this architecture via AuthMiddleware vs PolicyEngine).*

## 4. OPENBAO CREDENTIAL MANAGEMENT
**CURRENT Implementation:**
- **CredentialService**: Exposes `get("smtp")` dynamically.
- **OpenBaoProvider**: Handles the direct HTTP calls to `localhost:8200`.
- **AppRole authentication**: Activated by providing `OPENBAO_ROLE_ID` and `OPENBAO_SECRET_ID`.
- **Policy/Secret Path**: Requests data from `secret/data/mcp/smtp`.
- **How credentials are retrieved**: Performs a login with AppRole to get a Client Token, then does a GET to extract the internal Google App Password.
- **Failure**: Returns safe degradation (simulation mode in Gmail) if Vault is unreachable.
- **Caching (GAP)**: OpenBao credentials and Client Tokens are **NOT** currently cached. Real-world continuous loops will hit AppRole endpoints repeatedly.

## 5. AGENT / ORCHESTRATION FLOW
**CURRENT Implementation:**
- **`agent_request`**: Exposes the frontend prompt to the AI orchestrator.
- **Planner**: Groq analyzes text and generates a pseudo-code execution plan array.
- **DecisionEngine**: Maps the pseudo-plan to physical tool boundaries.
- **AgentRuntime**: Iterates through steps.
- **Authorization before execution**: Calls `rbac_policy_checker` lambda natively measuring `PolicyEngine.evaluate()`.
- **ExecutionEngine**: Sends the tool trigger down the pipeline.
- **ServerRegistry**: Looks up if the tool lives on Port 8101 or 8102, then makes an HTTP JSON-RPC POST call.

## 6. MCP PROTOCOL / ENDPOINTS
**CURRENT Supported Endpoints:**
- `POST /mcp`: Receives JSON-RPC 2.0 payloads (`tools/list`, `tools/call`, `agent_request`).
- `GET /mcp` & `GET /sse`: Server-Sent Events streams establishing `Session`.

## 7. PROJECT/FOLDER STRUCTURE
```
Custom_MCP_Server/
 ├── agents.yaml           - Defines users, roles, and allowed tool lists
 ├── config.yaml           - Global settings (auth, ports, JWT boundaries)
 ├── roles.yaml            - Master Role-based Access Ceilings
 ├── src/
 │   ├── agent/            - Orchestrator (Runtime, Decision, Execution, Groq LLM)
 │   ├── auth/             - JWT Validator, Middleware, SessionManager
 │   ├── common/           - Errors, Logging
 │   ├── credentials/      - CredentialService, OpenBaoProvider, EnvProvider
 │   ├── orchestration/    - ServerResolver (Cross-server mappings)
 │   ├── security/         - IdentityService, PolicyEngine, AuditLogger
 │   ├── servers/          - The target Microservices (gmail, time)
 │   ├── server.py         - Gateway Server (Port 8100)
 │   └── globals.py        - Global dependency injections
 ├── ui/                   - Web frontend HTML/JS (AI Hub)
 ├── tests/                - Pytest suites
 └── scripts/              - Helper scripts (generate_jwt.py, local-dev-openbao.sh)
```

## 8. CONFIGURATION
* `config.yaml`: Port settings, rate limits, SMTP fallback triggers.
* `agents.yaml`: User-to-Role bindings.
* `roles.yaml`: The strict authorization policy lists mapping tools.
* `.env`: Environment variables (holds JWT_SECRET, OpenBao Tokens). **MUST NEVER BE COMMITTED WITH REAL SECRETS.**
* `.env.example`: Template for developers.

## 9. INSTALLATION / SETUP (FIRST-TIME RUN)
**Prerequisites**: Python 3.11+, HashiCorp OpenBao (Vault Fork).

### A. Install OpenBao
OpenBao is required for securely managing SMTP credentials.
1. Download the latest release of OpenBao for your OS from the official repository: [OpenBao Releases (GitHub)](https://github.com/openbao/openbao/releases).
2. Extract the executable (`bao.exe` on Windows or `bao` on Linux/macOS).
3. Add the extracted package's folder to your system's `PATH` environment variable so you can run `bao` from anywhere.
4. Verify installation by running: `bao --version`.

### B. Python Setup
1. Create a virtual environment (optional but recommended): `python -m venv .venv` and activate it.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy the environment template: `cp .env.example .env` (fill in your LLM API keys for Groq/Gemini).

### C. Configure OpenBao Identity (Getting Role ID & Secret ID)
1. Start the OpenBao development server in a new terminal:
   ```bash
   bao server -dev
   ```
2. In the OpenBao server output, copy the **Root Token** (starts with `s.`). Ensure you leave this terminal running!
3. Open a separate terminal and authenticate your CLI with the root token:
   ```bash
   # On Linux/macOS/Git Bash:
   export BAO_TOKEN="s.YOUR_ROOT_TOKEN_HERE"
   
   # On Windows PowerShell:
   $env:BAO_TOKEN="s.YOUR_ROOT_TOKEN_HERE"
   ```
4. Run the credentials payload script to generate the AppRole securely (on Windows, use Git Bash/WSL):
   ```bash
   bash scripts/local-dev-openbao.sh
   ```
   **Alternative for Windows Users (Manual Method):** If you cannot run the bash script, run the following OpenBao CLI commands:
   ```powershell
   # 1. Enable AppRole
   bao auth enable approle

   # 2. Create the mcp-agent role
   bao write auth/approle/role/mcp-agent token_ttl=1h token_max_ttl=24h

   # 3. Get the Role ID
   bao read -field=role_id auth/approle/role/mcp-agent/role-id

   # 4. Generate a new Secret ID
   bao write -f -field=secret_id auth/approle/role/mcp-agent/secret-id
   ```

5. **Update `.env`**: Whether you used the bash script or manual commands, copy the resulting **Role ID** and **Secret ID** values and paste them into your `.env` file for `OPENBAO_ROLE_ID=` and `OPENBAO_SECRET_ID=`.

### D. Populate Secrets in OpenBao
Because running `bao server -dev` wipes its memory every time it is restarted, you must physical store credentials into the vault before the python servers can fetch them. 

Once your vault is running, run this command in your terminal to insert SMTP test credentials:
```bash
bao kv put secret/mcp/smtp username="dummy-user" password="dummy-password"
```
*(If you are setting up other tools in the future, you can similarly run `bao kv put secret/mcp/toolname...` thanks to the flexible wildcard policy setup).*

### E. Generate JWT for the Application
1. Generate an identity token for the dashboard: `python scripts/generate_jwt.py admin`
2. You will use this token in the UI or headers to authenticate against the MCP Server.

## 10. HOW TO RUN
- **Start whole cluster**: `python run_servers.py`
- **Development isolation**: 
  - `python -m src.server`
  - `python -m src.servers.gmail_server`
- **Tests**: `pytest tests/ -v`

## 11. EXAMPLE REQUEST FLOW
1. **User Request**: "Check the time in Tokyo."
2. **JWT**: Intercepted by `AuthMiddleware`.
3. **Orchestrator**: `AgentRuntime` passes string to Groq.
4. **Tool Selection**: Planner selects `get_current_datetime`.
5. **Authorization**: `PolicyEngine` confirms `admin` role allows this tool.
6. **Tool Execution**: `ExecutionEngine` proxies payload to Port 8102 (Time Server).
7. **Response**: JSON sent back to Groq, synthesized, and returned via SSE stream to UI.

## 12. TESTING
`pytest` covers:
- **Authentication**: `test_security_auth.py` evaluates token failures and identity matching.
- **Authorization**: `test_policy_engine.py` evaluates Ceilings and Blocklists.
- **Credentials/OpenBao**: `test_credentials.py` testing fallback and validation.
- **Integration**: `test_server_health.py`.
*(Note: Requires `pytest-asyncio` for executing async client endpoints).*

## 13. AUDIT / OBSERVABILITY
**CURRENT**: Leverages structured `logger` inside `PolicyEngine`, `AuthMiddleware`, and `AgentRuntime`.
Logs `authorization_allowed`, `authorization_denied`, `authentication_failure`.
**Protections**: Does not dump raw prompts or stack traces with secret content. Ties events natively to standard HTTP `correlation_id` across microservices.

## 14. SECURITY NOTES
**CURRENT**: 
- Validates JWT Signatures using symmetric keys, stripping identities gracefully.
- Policy Checks natively block unlisted tools.
- OpenBao handles credentials via Memory (zero-disk touch).

## 15. PERFORMANCE & OPTIMIZATIONS (CURRENT)
- **Parallel Processing**: MCP Array Requests use native `asyncio.gather` for simultaneous JSON-RPC parallel execution, bypassing sequential timeouts.
- **Dynamic Policy Checks**: `AgentRuntime` checks exact server namespaces (`gmail`, `time`) iteratively on the fly to support distinct permissions per-server.
- **In-Memory Vault TTL**: OpenBao Vault `AppRole` login natively caches client tokens and fetched secrets with a strict 300s (5-minute) timeout, terminating DDoS risks on large prompts.

## 16. FUTURE WORK / PLANNED
- [FUTURE] **Cloud Workload Identity**: Deprecate `.env` usage natively in favor of true Kubernetes `serviceaccount` injection files for Vault authentication.
- [FUTURE] **Cloud IDP**: Retire hardcoded JSON Web Tokens in `index.html` by enforcing an Okta/Auth0 integration inside the front-end login component.

## 17. TROUBLESHOOTING

### OpenBao ConnectionError / Credential Failure
If you see `Failed to authenticate with OpenBao: ConnectionError` in the logs, it means the OpenBao development server has stopped or reset, wiping your in-memory credentials.

**To Fix:**
1. **Remove Old IDs**: In your `.env` file, delete the `OPENBAO_ROLE_ID=` and `OPENBAO_SECRET_ID=` lines.
2. **Start OpenBao**: Open a new terminal and run `bao server -dev`. Leave this running.
3. **Copy Root Token**: Look at the startup output of the OpenBao server and copy the Root Token (usually starts with `s.`).
4. **Run Setup Script**: In a separate terminal, export the token and run the setup script:
   ```bash
   export BAO_TOKEN="s.YOUR_NEW_ROOT_TOKEN_HERE"
   bash scripts/local-dev-openbao.sh
   ```
5. **Update `.env`**: The script will output a `.env.local` file. Copy the fresh `OPENBAO_ROLE_ID` and `OPENBAO_SECRET_ID` from it and paste them back into your `.env`.
6. **Restart**: Restart your MCP servers (`python run_servers.py`).
