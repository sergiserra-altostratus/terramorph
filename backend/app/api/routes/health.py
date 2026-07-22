"""Health and auth status endpoints."""

from fastapi import APIRouter

from app.core.credentials import check_authentication

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint (public - no auth required)."""
    auth_status = check_authentication()
    return {
        "status": "ok",
        "version": "0.1.0",
        "gcp_authenticated": auth_status["authenticated"],
    }


@router.get("/health/token")
async def get_api_token() -> dict:
    """Get the API token (shown only in health endpoint for initial setup)."""
    from app.core.auth import get_or_create_token, AUTH_DISABLED
    if AUTH_DISABLED:
        return {"auth_enabled": False, "message": "Authentication is disabled (TERRAMORPH_AUTH_DISABLED=true)"}
    token = get_or_create_token()
    return {"auth_enabled": True, "token": token}


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


@router.get("/history")
async def job_history(limit: int = 20, type: str | None = None) -> dict:
    """Get job history."""
    from app.services.persistence import get_job_history
    jobs = get_job_history(limit=limit, job_type=type)
    return {"jobs": jobs, "total": len(jobs)}


@router.get("/generations")
async def generation_history(limit: int = 10) -> dict:
    """Get recent generation history."""
    from app.services.persistence import get_generation_history
    generations = get_generation_history(limit=limit)
    return {"generations": generations, "total": len(generations)}


@router.get("/generations/{generation_id}")
async def get_generation(generation_id: str) -> dict:
    """Get a specific generation result with full file contents."""
    from app.services.persistence import get_generation_by_id
    result = get_generation_by_id(generation_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Generation not found")
    return result


@router.get("/audit")
async def audit_log(limit: int = 50, category: str | None = None) -> dict:
    """Get audit log entries."""
    from app.services.persistence import get_audit_log
    entries = get_audit_log(limit=limit, category=category)
    return {"entries": entries, "total": len(entries)}
