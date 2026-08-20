"""Terraform plan output cache.

Caches plan results by SHA256 hash of the input .tf files.
Avoids re-running expensive terraform plan when files haven't changed.
TTL: 5 minutes (configurable).
"""

import hashlib
import time
from typing import Any

from app.core.logging import get_logger

logger = get_logger("plan_cache")

# In-memory cache: hash -> {stdout, stderr, rc, timestamp}
_plan_cache: dict[str, dict[str, Any]] = {}

# TTL in seconds (5 minutes)
CACHE_TTL = 300

# Max cache entries (prevent unbounded memory growth)
MAX_CACHE_ENTRIES = 50


def _compute_hash(tf_files: dict[str, str]) -> str:
    """Compute a deterministic SHA256 hash of all .tf file contents."""
    hasher = hashlib.sha256()
    # Sort by filename for deterministic ordering
    for filename in sorted(tf_files.keys()):
        hasher.update(filename.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(tf_files[filename].encode("utf-8"))
        hasher.update(b"\x00")
    return hasher.hexdigest()[:16]


def get_cached_plan(tf_files: dict[str, str]) -> tuple[str, str, int] | None:
    """Get cached plan result if available and not expired.

    Args:
        tf_files: Dict of filename -> content to hash.

    Returns:
        Tuple of (stdout, stderr, returncode) if cached, None otherwise.
    """
    _evict_expired()

    file_hash = _compute_hash(tf_files)
    entry = _plan_cache.get(file_hash)

    if entry is None:
        return None

    # Check TTL
    if time.time() - entry["timestamp"] > CACHE_TTL:
        del _plan_cache[file_hash]
        return None

    logger.info(f"Plan cache HIT (hash={file_hash})")
    return entry["stdout"], entry["stderr"], entry["rc"]


def cache_plan_result(tf_files: dict[str, str], stdout: str, stderr: str, rc: int) -> None:
    """Cache a plan result.

    Only caches successful plans (rc == 0) to avoid caching transient errors.
    """
    if rc != 0:
        return

    _evict_expired()

    # Enforce max entries
    if len(_plan_cache) >= MAX_CACHE_ENTRIES:
        # Remove oldest entry
        oldest_key = min(_plan_cache, key=lambda k: _plan_cache[k]["timestamp"])
        del _plan_cache[oldest_key]

    file_hash = _compute_hash(tf_files)
    _plan_cache[file_hash] = {
        "stdout": stdout,
        "stderr": stderr,
        "rc": rc,
        "timestamp": time.time(),
    }
    logger.info(f"Plan cache STORE (hash={file_hash}, entries={len(_plan_cache)})")


def invalidate_cache() -> None:
    """Clear the entire plan cache."""
    _plan_cache.clear()
    logger.info("Plan cache CLEARED")


def _evict_expired() -> None:
    """Remove expired entries from cache."""
    now = time.time()
    expired = [k for k, v in _plan_cache.items() if now - v["timestamp"] > CACHE_TTL]
    for k in expired:
        del _plan_cache[k]
