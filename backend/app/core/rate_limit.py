"""Simple in-memory rate limiting middleware.

Limits requests per client IP on expensive endpoints (discovery, generation,
drift, auto-import). Lightweight — no external dependencies required.

Default: 30 requests per minute per IP on protected endpoints.
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("rate_limit")

# Rate limit configuration
RATE_LIMIT_REQUESTS = 30  # max requests
RATE_LIMIT_WINDOW = 60  # per X seconds

# Endpoints subject to rate limiting (POST endpoints that trigger expensive operations)
RATE_LIMITED_PREFIXES = [
    "/api/v1/discovery/start",
    "/api/v1/generate/",
    "/api/v1/drift/start",
    "/api/v1/auto-import/start",
    "/api/v1/bulk-export/start",
    "/api/v1/state/graph",
    "/api/v1/aws/discovery/start",
]

# In-memory request tracking: {ip: [(timestamp, ...), ...]}
_request_log: dict[str, list[float]] = defaultdict(list)


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request (respects X-Forwarded-For for proxied setups)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limited(path: str) -> bool:
    """Check if a path should be rate-limited."""
    return any(path.startswith(prefix) for prefix in RATE_LIMITED_PREFIXES)


def _cleanup_old_entries(ip: str, now: float) -> None:
    """Remove entries outside the current window."""
    cutoff = now - RATE_LIMIT_WINDOW
    _request_log[ip] = [ts for ts in _request_log[ip] if ts > cutoff]
    # Prevent memory leak: remove IPs with no recent requests
    if not _request_log[ip]:
        del _request_log[ip]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limits on expensive API endpoints."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only rate-limit specific endpoints
        if not _is_rate_limited(path):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        now = time.time()

        # Cleanup old entries
        _cleanup_old_entries(client_ip, now)

        # Check rate limit
        if len(_request_log[client_ip]) >= RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW}s. Try again later.",
            )

        # Record this request
        _request_log[client_ip].append(now)

        return await call_next(request)
