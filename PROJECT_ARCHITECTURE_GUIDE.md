# 🚀 Multi-Server Model Context Protocol (MCP) Architecture Guide

Welcome! This document provides a complete, easy-to-understand guide to the **Multi-Server MCP Architecture** and **Groq AI Agent Hub**.

---

## 📌 Table of Contents
1. [What is Model Context Protocol (MCP)?](#-what-is-model-context-protocol-mcp)
2. [High-Level Architecture Diagram](#-high-level-architecture-diagram)
3. [The 4 Microservice Servers](#-the-4-microservice-servers)
4. [Complete Catalog of the 10 MCP Tools](#-complete-catalog-of-the-10-mcp-tools)
5. [User Authentication & Access Control (RBAC)](#-user-authentication--access-control-rbac)
6. [Security Guardrails & Enterprise Protections](#-security-guardrails--enterprise-protections)
7. [How to Run & Test the Project](#-how-to-run--test-the-project)
8. [Connecting External MCP Clients (Inspector, Claude, Cursor)](#-connecting-external-mcp-clients)
9. [Developer Guide: Adding/Removing Servers & Tools](#-developer-guide-adding-new-servers--tools-in-minutes)

---

## 🌟 What is Model Context Protocol (MCP)?

**Model Context Protocol (MCP)** is an open industry standard developed by Anthropic that allows AI models (like Groq, Claude, ChatGPT, Gemini) to securely discover and invoke local functions, databases, and APIs without exposing private server infrastructure.

Instead of hardcoding APIs into an AI prompt, MCP allows servers to expose **tools** via standard **JSON-RPC 2.0 protocol over HTTP and Server-Sent Events (SSE)**.

---

## 🗺️ High-Level Architecture Diagram

```
                        ┌─────────────────────────────────────────────────────────────┐
                        │                     User Input Prompt                       │
                        │      (e.g., "Show me all active Engineering projects")      │
                        └──────────────────────────────┬──────────────────────────────┘
                                                       │
                                                       ▼
                        ┌─────────────────────────────────────────────────────────────┐
                        │             Groq LLM (Native Function Calling)             │
                        │        Evaluates all 10 Tool JSON-Schemas Dynamically       │
                        └──────────────┬──────────────────────────────┬───────────────┘
                                       │                              │
                    [Tool Call Required]                      [Direct Answer]
                                       │                              │
                                       ▼                              ▼
                 ┌──────────────────────────────────────────┐   ┌────────────────────────┐
                 │      Dynamic Client-Side Dispatcher      │   │  Conversational Answer │
                 │    Routes tool to 8101, 8102, or 8103    │   │  (General Knowledge)   │
                 └─────────────────────┬────────────────────┘   └────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
      ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
      │ Gmail MCP (:8101) │ │ Time MCP (:8102)  │ │ Database (:8103)  │
      │ - send_email      │ │ - get_datetime    │ │ - query_projects  │
      │ - read_inbox      │ │ - convert_tz      │ │ - get_evidence    │
      │ - search_emails   │ │ - system_uptime   │ │ - list_projects   │
      │ - create_draft    │ └─────────┬─────────┘ └─────────┬─────────┘
      └─────────┬─────────┘           │                     │
                └─────────────────────┼─────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │    Live JSON Result Received     │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │       Agent Synthesis Pass       │
                    │   LLM synthesizes final answer   │
                    └─────────────────┬────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │  Rendered to User in Web UI Hub  │
                    └──────────────────────────────────┘
```

---

## 🏛️ The 4 Microservice Servers

| Server Component | Port | Endpoint URL | Responsibilities |
|---|---|---|---|
| **🌐 AI Agent Hub & Gateway** | `8100` | `http://localhost:8100` | • Single-Page Web UI interface<br>• Master MCP Gateway consolidating all tools<br>• Session authentication & login portal |
| **📧 Gmail MCP Server** | `8101` | `http://localhost:8101/mcp` | • Real-time Gmail SMTP email dispatch<br>• IMAP inbox reader & keyword search<br>• Gmail draft creation |
| **🕒 Time & System MCP Server** | `8102` | `http://localhost:8102/mcp` | • Host hardware clock & ISO-8601 formatting<br>• Multi-timezone converter (12h/24h AM/PM)<br>• Server uptime & OS diagnostic metrics |
| **🗄️ Postgres Database Server** | `8103` | `http://localhost:8103/mcp` | • Real SQL querying on `projects` dataset<br>• Project evidence and knowledge retrieval<br>• Department & status classification filtering |

---

## 🛠️ Complete Catalog of the 10 MCP Tools

### 📧 Domain 1: Gmail MCP Server (`Port 8101`)

#### 1. `send_email`
* **Purpose:** Dispatches an outgoing email via Gmail SMTP.
* **Input Parameters:**
  * `to` *(string, required)*: Recipient email address (e.g. `bonthumanoj999@gmail.com`).
  * `subject` *(string, required)*: Subject line of the email.
  * `body` *(string, required)*: Text body of the email.

#### 2. `read_inbox`
* **Purpose:** Reads and summarizes the most recent incoming emails from your inbox.
* **Input Parameters:**
  * `max_results` *(integer, optional, default: 5)*: Number of emails to retrieve.

#### 3. `search_emails`
* **Purpose:** Searches through inbox messages and drafts for specific keywords or senders.
* **Input Parameters:**
  * `query` *(string, optional, default: "")*: Keyword or phrase to search.

#### 4. `create_draft`
* **Purpose:** Prepares an email draft in Gmail without sending it immediately.
* **Input Parameters:**
  * `to` *(string, required)*: Target recipient.
  * `subject` *(string, required)*: Draft subject.
  * `body` *(string, required)*: Draft body.

---

### 🕒 Domain 2: Time & System MCP Server (`Port 8102`)

#### 5. `get_current_datetime`
* **Purpose:** Reads the exact live host operating system hardware clock.
* **Input Parameters:**
  * `timezone` *(string, optional)*: IANA timezone name (e.g. `"Asia/Kolkata"`, `"UTC"`, `"America/New_York"`, `"Asia/Tokyo"`).

#### 6. `convert_timezone`
* **Purpose:** Converts timestamps between international timezones.
* **Input Parameters:**
  * `time_str` *(string, required)*: Time to convert (supports `"04:30 PM"`, `"16:30"`, or `"2026-08-19 14:30:00"`).
  * `from_tz` *(string, default: "UTC")*: Source timezone (e.g. `"America/New_York"`, `"EST"`).
  * `to_tz` *(string, required)*: Destination timezone (e.g. `"Asia/Kolkata"`, `"IST"`).

#### 7. `get_system_uptime`
* **Purpose:** Provides server health metrics, operating system version, and server runtime duration.
* **Input Parameters:** None (`{}`).

---

### 🗄️ Domain 3: Postgres Database MCP Server (`Port 8103`)

#### 8. `query_projects`
* **Purpose:** Runs real parameterized SQL `SELECT` queries or dynamic department/status lookups against the projects table.
* **Input Parameters:**
  * `sql_query` *(string, optional)*: Custom read-only SQL query (e.g. `"SELECT name, budget, status FROM projects WHERE department = 'Engineering'"`).
  * `department` *(string, optional)*: Filter by department (`"Engineering"`, `"Operations"`, `"Security"`, `"AI & Data"`).
  * `status` *(string, optional)*: Filter by status (`"Active"`, `"Completed"`, `"In Review"`).
  * `lead_name` *(string, optional)*: Filter by lead engineer.
  * `limit` *(integer, default: 10)*: Maximum rows to return.

#### 9. `get_project_evidence`
* **Purpose:** Retrieves complete knowledge evidence summaries, delivery metrics, and project lead info for a specific project.
* **Input Parameters:**
  * `project_name` *(string, required)*: Name or ID of the project (e.g. `"Project Apollo"`, `"Enterprise MCP Gateway"`).

#### 10. `list_all_projects`
* **Purpose:** Returns a catalog of all enterprise projects, department assignments, and budgets.
* **Input Parameters:**
  * `department` *(string, optional)*: Optional department filter.
  * `status` *(string, optional)*: Optional status filter.

---

## 🔐 User Authentication & Access Control (RBAC)

The system enforces authentication using **Bearer Tokens** and pre-configured user credentials:

| Username | Password | Role / Identity | Permissions |
|---|---|---|---|
| **`vishal`** | `vishal123` | `Lead Platform Engineer` | 🟢 **Full Admin** (All 10 Tools) |
| **`vinod`** | `vinod123` | `Senior Operations Lead` | 🟢 **Full Admin** (All 10 Tools) |
| **`admin`** | `admin123` | `Security Administrator` | 🟢 **Superuser** (All 10 Tools) |
| **`agent_alpha`** | `alpha123` | `Automated Worker` | 🟡 Standard Agent |
| **`agent_beta`** | `beta123` | `Restricted Worker` | 🟠 Restricted Read-Only |

---

## 🛡️ Security Guardrails & Enterprise Protections

1. **Read-Only Database Query Enforcer**:
   * All SQL execution is strictly validated. Statements attempting mutation (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`) are blocked immediately.
2. **Security Allowlist**:
   * Emails can only be dispatched to explicitly verified email domains and addresses defined in `config.yaml` (`bonthumanoj999@gmail.com`, `vishalreddykonreddy@gmail.com`).
3. **Prompt Injection Defense**:
   * Inspects outgoing email and database queries for adversarial prompt injection attempts.
4. **Sliding-Window Rate Limiter**:
   * Restricts callers to a maximum number of calls within a 60-second window to prevent Denial-of-Service (DoS).
5. **Dual-Port SMTP Fallback & Socket Timeouts**:
   * Attempts Port 587 (TLS) and Port 465 (SSL) with a 5-second socket timeout.
6. **Tamper-Evident SHA-256 Audit Trail**:
   * Records cryptographic transaction hashes in `audit.db` SQLite core.

---

## 🚀 How to Run & Test the Project

### 1. Launch All 4 Servers in One Command
```bash
python run_servers.py
```

Startup banner:
```
======================================================================
🚀 STARTING MULTI-MCP SERVER ARCHITECTURE
======================================================================
  🌐 Web UI & AI Agent Hub     → http://localhost:8100
  📧 Gmail MCP Server           → http://localhost:8101/mcp (Tools: send, read, search, draft)
  🕒 Time & System MCP Server   → http://localhost:8102/mcp (Tools: datetime, timezone, uptime)
  🗄️ Database MCP Server       → http://localhost:8103/mcp (Tools: query_projects, get_evidence, list)
======================================================================
```

### 2. Open the Web Hub in Your Browser
Visit **[http://localhost:8100](http://localhost:8100)** and log in with:
* **Username**: `vishal`
* **Password**: `vishal123`

---

## 🔌 Connecting External MCP Clients

Connect external tools directly:
* **MCP Inspector**: `npx @modelcontextprotocol/inspector`
* **Target URLs**:
  * Unified Gateway: `http://localhost:8100/mcp`
  * Gmail Server: `http://localhost:8101/mcp`
  * Time Server: `http://localhost:8102/mcp`
  * Database Server: `http://localhost:8103/mcp`
* **Header**: `Authorization: Bearer vishal-test-token`
