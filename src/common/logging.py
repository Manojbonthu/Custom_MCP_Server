"""
logging.py — Structured JSON logging setup.

Call setup_logging() once at server startup.
All loggers across the app will emit JSON lines:
  {"level": "INFO", "logger": "src.channels.mail.tools", "message": "...", "time": "..."}
"""

import logging
import json
import sys


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger with JSON output to stdout.
    Call once at server startup in server.py.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)
