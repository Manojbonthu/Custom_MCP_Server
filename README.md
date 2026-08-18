# notifications-mcp

> **Unified Notifications MCP Server** — Phase 1: Gmail  
> Send email alerts from any AI agent (Claude, LangGraph, GPT) via the Model Context Protocol.

---

## What This Does

This MCP server exposes a `mail_send` tool that any MCP-compatible AI agent can call to send emails via Gmail.

**Use case:** A factory machine stops working → your AI monitoring agent calls `mail_send` → manager, technician, and staff all receive an alert email instantly.

```
Machine stops → AI Agent → mail_send tool → Gmail → Manager + Technician notified
```

**MCP endpoint:** `http://localhost:8100/mcp`

---

## Architecture

```
notifications-mcp/
├── src/
│   ├── server.py          ← Entrypoint (Streamable HTTP + OAuth routes)
│   ├── config.py          ← Loads config.yaml
│   ├── registry.py        ← Dynamically loads channel tools
│   └── channels/
│       ├── mail/          ← Gmail channel (Phase 1)
│       ├── teams/         ← Microsoft Teams (Phase 2 placeholder)
│       └── sms/           ← SMS via Twilio (Phase 3 placeholder)
```

To add a new channel: create `channels/<name>/tools.py` with a `register(mcp, cfg)` function, add the channel name to `enabled_channels` in `config.yaml`. No other files change.

---

## Setup

### 1. Prerequisites

- Python 3.11+
- A Google Cloud project with the Gmail API enabled

### 2. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable the **Gmail API** for your project
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Web application**
5. Add Authorized redirect URI: `http://localhost:8100/auth/gmail/callback`
6. Download the JSON → save as `credentials/google_credentials.json`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
# or for development:
pip install -e ".[dev]"
```

### 4. Start the Server

```bash
python -m src.server
```

You'll see:
```
{"level": "INFO", "message": "Starting notifications-mcp | host=0.0.0.0 | port=8100"}
{"level": "INFO", "message": "MCP endpoint  → http://localhost:8100/mcp"}
{"level": "INFO", "message": "Gmail OAuth   → http://localhost:8100/auth/gmail/start"}
```

### 5. Authenticate Gmail (First Time Only)

Open your browser and visit:
```
http://localhost:8100/auth/gmail/start
```

1. You'll be redirected to Google's consent page
2. Log in with the Gmail account you want to send FROM
3. Grant the "Send email" permission
4. You'll see ✅ Gmail Authenticated! — close the tab
5. The token is saved to `credentials/gmail_token.json` and auto-refreshes silently from now on

---

## Using the `mail_send` Tool

### From MCP Inspector (testing)

```bash
npx @modelcontextprotocol/inspector http://localhost:8100/mcp
```

Call `mail_send` with:
```json
{
  "to": ["manager@yourcompany.com", "technician@yourcompany.com"],
  "subject": "ALERT: Machine #3 stopped",
  "body": "Machine #3 on Floor B stopped at 18:02.\nError code: E-404.\nPlease investigate immediately."
}
```

### From an AI Agent (Claude / LangGraph)

The agent sees this tool description:
> **mail_send** — Send an email via Gmail to one or more recipients. For factory machine downtime alerts, include the machine name, location, stop time, and error code.

The agent calls it as:
```python
result = await client.call_tool("mail_send", {
    "to": ["manager@factory.com", "tech@factory.com"],
    "subject": "ALERT: Machine #3 stopped",
    "body": "Machine #3 stopped at 18:02. Error: E-404. Location: Floor B, Line 2."
})
```

### From Antigravity / Claude Desktop

Add to your MCP config:
```json
{
  "mcpServers": {
    "notifications": {
      "url": "http://localhost:8100/mcp"
    }
  }
}
```

---

## Tool Reference

### `mail_send`

Send an email to one or more recipients via Gmail.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `to` | `list[str]` | ✅ | List of recipient email addresses |
| `subject` | `str` | ✅ | Email subject line |
| `body` | `str` | ✅ | Email body (plain text) |
| `cc` | `list[str]` | ❌ | CC recipients |
| `bcc` | `list[str]` | ❌ | BCC recipients |

**Returns on success:**
```json
{"status": "sent", "message_id": "18b3c...", "recipients": ["manager@co.com"]}
```

**Returns on failure:**
```json
{"status": "failed", "error": "rate_limited", "message": "Gmail rate limit hit. Wait 60s."}
```

---

## Configuration

Edit `config.yaml` to change settings:

```yaml
server:
  host: "0.0.0.0"
  port: 8100          # Change port here

enabled_channels:
  - mail              # Add 'teams' or 'sms' here in Phase 2/3

channels:
  mail:
    credentials_path: "credentials/google_credentials.json"
    token_path: "credentials/gmail_token.json"
    scopes:
      - "https://www.googleapis.com/auth/gmail.send"
    oauth_redirect_uri: "http://localhost:8100/auth/gmail/callback"
```

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output:
```
tests/channels/mail/test_tools.py::test_mail_send_success PASSED
tests/channels/mail/test_tools.py::test_mail_send_not_authenticated PASSED
tests/channels/mail/test_tools.py::test_mail_send_rate_limited PASSED
tests/channels/mail/test_tools.py::test_mail_send_missing_to_field PASSED
tests/channels/mail/test_tools.py::test_mail_send_missing_subject PASSED
tests/channels/mail/test_tools.py::test_mail_send_multiple_recipients PASSED
tests/channels/mail/test_tools.py::test_mail_send_with_cc_bcc PASSED
```

---

## Adding Phase 2 (Teams) or Phase 3 (SMS)

1. Create the channel folder:
   ```
   src/channels/teams/__init__.py
   src/channels/teams/auth.py
   src/channels/teams/client.py
   src/channels/teams/schemas.py
   src/channels/teams/tools.py   ← must have def register(mcp, cfg)
   ```
2. Add to `config.yaml`:
   ```yaml
   enabled_channels:
     - mail
     - teams       ← add this
   channels:
     teams:
       tenant_id: "..."
       client_id: "..."
   ```
3. **Done.** `server.py` and `registry.py` need zero changes.

---

## Security Notes

- `credentials/` is gitignored — never commit Google credentials
- OAuth token auto-refreshes silently — you only consent once
- The server runs on localhost — not exposed to the internet by default
- No API key required for localhost use

---

*Phase 1: Gmail ✅ | Phase 2: Teams 🔜 | Phase 3: SMS 🔜*
