"""API Bearer token authentication middleware.

Generates a token on first run and requires it for all API calls.
Token is stored in the SQLite database.
Can be disabled via TERRAMORPH_AUTH_DISABLED=true env var for local development.
"""

import os
import secrets

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.services.persistence import load, save

logger = get_logger("auth")

AUTH_KEY = "api_token"
AUTH_DISABLED = os.environ.get("TERRAMORPH_AUTH_DISABLED", "false").lower() == "true"

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/api/v1/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def get_or_create_token() -> str:
    """Get existing token or generate a new one on first run."""
    token = load(AUTH_KEY)
    if token:
        return token
    # Generate new token
    token = f"tm_{secrets.token_urlsafe(32)}"
    save(AUTH_KEY, token)
    logger.info(f"Generated new API token: {token[:10]}...")
    return token


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates Bearer token on all API requests."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth if disabled (dev mode)
        if AUTH_DISABLED:
            return await call_next(request)

        # Skip public paths
        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # Skip WebSocket
        if path.startswith("/ws/"):
            return await call_next(request)

        # Validate token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header. Use: Authorization: Bearer <token>")

        provided_token = auth_header[7:]  # Remove "Bearer "
        expected_token = get_or_create_token()

        if not secrets.compare_digest(provided_token, expected_token):
            raise HTTPException(status_code=401, detail="Invalid API token")

        return await call_next(request)
