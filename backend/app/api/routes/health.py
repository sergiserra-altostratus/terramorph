"""Health and auth status endpoints."""

from fastapi import APIRouter

from app.core.credentials import check_authentication

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    auth_status = check_authentication()
    return {
        "status": "ok",
        "version": "0.1.0",
        "gcp_authenticated": auth_status["authenticated"],
    }


@router.get("/auth/status")
async def auth_status() -> dict:
    """Check GCP authentication status."""
    return check_authentication()
