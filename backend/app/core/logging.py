"""Structured logging configuration."""

import logging
import sys

from app.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    level = getattr(logging, settings.terramorph_log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    # Suppress noisy GCP SDK logs
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance."""
    return logging.getLogger(f"terramorph.{name}")
