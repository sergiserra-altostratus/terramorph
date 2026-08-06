"""Structured logging configuration with JSON output and correlation IDs."""

import logging
import json
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from app.config import settings

# Context variable for correlation ID (propagated across async tasks)
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return _correlation_id.get()


def set_correlation_id(cid: str | None = None) -> str:
    """Set correlation ID for the current context. Generates one if not provided."""
    if not cid:
        cid = str(uuid.uuid4())[:8]
    _correlation_id.set(cid)
    return cid


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Add correlation ID if present
        cid = _correlation_id.get()
        if cid:
            log_entry["cid"] = cid

        # Add extra fields if present
        if hasattr(record, "job_id"):
            log_entry["job_id"] = record.job_id
        if hasattr(record, "phase"):
            log_entry["phase"] = record.phase

        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_entry["error"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        cid = _correlation_id.get()
        cid_str = f" [{cid}]" if cid else ""
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
        msg = f"{ts} | {record.levelname:<8} | {record.name}{cid_str} | {record.getMessage()}"
        if record.exc_info and record.exc_info[0]:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


def setup_logging() -> None:
    """Configure structured logging for the application."""
    level = getattr(logging, settings.terramorph_log_level.upper(), logging.INFO)
    env = getattr(settings, "terramorph_env", "development")

    # Use JSON in production, human-readable in development
    if env == "production":
        formatter = StructuredFormatter()
    else:
        formatter = HumanFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Suppress noisy SDK logs
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(f"terramorph.{name}")
