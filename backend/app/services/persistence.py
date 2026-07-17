"""Persistence layer for storing application data as JSON files.

Data is stored in /app/data/ which is mounted as a Docker volume
to survive container restarts.
"""

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.logging import get_logger

logger = get_logger("persistence")

DATA_DIR = Path(os.environ.get("TERRAMORPH_DATA_DIR", "/app/data"))

_write_lock = Lock()


def _ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load(filename: str, default: Any = None) -> Any:
    """Load data from a JSON file.

    Args:
        filename: Name of the JSON file (e.g., 'ai_settings.json').
        default: Default value if file doesn't exist or is invalid.

    Returns:
        Parsed JSON data, or default if file doesn't exist.
    """
    filepath = DATA_DIR / filename
    if not filepath.exists():
        return default

    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load {filename}: {e}")
        return default


def save(filename: str, data: Any) -> None:
    """Save data to a JSON file atomically.

    Uses write-to-temp-then-rename for crash safety.

    Args:
        filename: Name of the JSON file.
        data: Data to serialize as JSON.
    """
    _ensure_data_dir()
    filepath = DATA_DIR / filename
    tmp_filepath = DATA_DIR / f".{filename}.tmp"

    with _write_lock:
        try:
            with open(tmp_filepath, "w") as f:
                json.dump(data, f, indent=2, default=str)
            tmp_filepath.replace(filepath)
        except IOError as e:
            logger.error(f"Failed to save {filename}: {e}")
            if tmp_filepath.exists():
                tmp_filepath.unlink()
