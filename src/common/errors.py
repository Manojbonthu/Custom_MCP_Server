"""
errors.py — Maps Gmail API exceptions to clean, agent-readable error dicts.

The AI agent receives a structured dict instead of a raw Python traceback.
This lets the agent understand what went wrong and decide what to do next.
"""

import logging

logger = logging.getLogger(__name__)


def handle_gmail_error(exc: Exception) -> dict:
    """
    Convert any Gmail API exception into a clean MCP tool error response dict.

    Returns a dict with keys:
      - status: always "failed"
      - error:  short machine-readable error code
      - message: human-readable explanation for the AI agent
    """
    # Import here to avoid making googleapiclient a required import at module level
    try:
        from googleapiclient.errors import HttpError
        if isinstance(exc, HttpError):
            status_code = exc.resp.status
            logger.error(f"Gmail HttpError {status_code}: {exc.reason}")

            if status_code == 401:
                return {
                    "status": "failed",
                    "error": "auth_expired",
                    "message": (
                        "Gmail token has expired or been revoked. "
                        "Visit http://localhost:8100/auth/gmail/start to re-authenticate."
                    ),
                }
            elif status_code == 429:
                return {
                    "status": "failed",
                    "error": "rate_limited",
                    "message": "Gmail API rate limit hit. Wait 60 seconds and retry.",
                }
            elif status_code == 400:
                return {
                    "status": "failed",
                    "error": "invalid_input",
                    "message": f"Gmail rejected the request: {exc.reason}",
                }
            elif status_code == 403:
                return {
                    "status": "failed",
                    "error": "permission_denied",
                    "message": (
                        "Gmail API permission denied. "
                        "Ensure the gmail.send scope is granted and re-authenticate."
                    ),
                }
            else:
                return {
                    "status": "failed",
                    "error": f"gmail_http_{status_code}",
                    "message": f"Gmail API error {status_code}: {exc.reason}",
                }
    except ImportError:
        pass

    # Generic fallback for any other exception
    logger.error(f"Unexpected error in mail channel: {type(exc).__name__}: {exc}")
    return {
        "status": "failed",
        "error": "unknown",
        "message": f"{type(exc).__name__}: {str(exc)}",
    }
