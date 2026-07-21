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


@router.get("/onboarding/status")
async def onboarding_status() -> dict:
    """Check if onboarding is needed (first run detection).

    Onboarding is considered complete when at least one cloud provider
    is configured (GCP authenticated or AWS configured).
    """
    from app.services.aws_credentials import is_aws_configured
    from app.services.ai_settings import is_ai_configured

    gcp_auth = check_authentication()
    aws_configured = is_aws_configured()
    ai_configured = is_ai_configured()

    # Onboarding is needed if no cloud provider is ready
    cloud_ready = gcp_auth["authenticated"] or aws_configured
    onboarding_complete = cloud_ready

    return {
        "onboarding_needed": not onboarding_complete,
        "steps": {
            "cloud_provider": cloud_ready,
            "gcp_authenticated": gcp_auth["authenticated"],
            "aws_configured": aws_configured,
            "ai_configured": ai_configured,
        },
    }


@router.get("/auth/status")
async def auth_status() -> dict:
    """Check GCP authentication status."""
    return check_authentication()
