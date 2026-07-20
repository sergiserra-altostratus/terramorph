"""Drift detection and auto-fix API endpoints.

Prerequisites (enforced):
- AI provider must be configured in Settings
- Remote backend (GCS bucket) must be specified in the request
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_settings import is_ai_configured, get_active_config
from app.services.drift import start_drift_detection, get_drift_job_status

router = APIRouter()


class DriftDetectionRequest(BaseModel):
    """Request to start drift detection."""

    tf_files: dict[str, str] = Field(
        description="Dict of filename → HCL content to check for drift"
    )
    bucket: str = Field(description="GCS bucket name for remote state")
    prefix: str = Field(description="State prefix in the bucket")
    project_id: str = Field(description="GCP project ID")


@router.post("/drift/start")
async def start_drift(request: DriftDetectionRequest) -> dict:
    """Start drift detection and auto-fix.

    Prerequisites:
    - AI provider must be configured
    - GCS backend must be specified
    """
    # Validation: AI must be configured
    if not is_ai_configured():
        raise HTTPException(
            status_code=412,
            detail="AI provider is not configured. Go to Settings and configure at least one AI provider before using drift detection.",
        )

    # Validation: Backend state must be specified
    if not request.bucket or not request.bucket.strip():
        raise HTTPException(
            status_code=412,
            detail="Remote backend (GCS bucket) is required for drift detection. Specify a bucket name.",
        )

    if not request.tf_files:
        raise HTTPException(
            status_code=400,
            detail="No Terraform files provided. Generate code first.",
        )

    # Validation: Verify AI config has valid key
    ai_config = get_active_config()
    if not ai_config or not ai_config.api_key:
        raise HTTPException(
            status_code=412,
            detail="AI provider API key is missing or invalid. Check your configuration in Settings.",
        )

    job_id = await start_drift_detection(
        tf_files=request.tf_files,
        bucket=request.bucket.strip(),
        prefix=request.prefix.strip(),
        project_id=request.project_id.strip(),
    )

    return {"job_id": job_id, "status": "running"}


@router.get("/drift/status/{job_id}")
async def drift_status(job_id: str) -> dict:
    """Get drift detection job status."""
    job = get_drift_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Drift job '{job_id}' not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "error": job.get("error"),
    }


@router.get("/drift/results/{job_id}")
async def drift_results(job_id: str) -> dict:
    """Get drift detection full results."""
    job = get_drift_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Drift job '{job_id}' not found")
    if job["status"] == "running":
        raise HTTPException(status_code=409, detail="Job still running. Check status first.")
    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job.get("result"),
        "error": job.get("error"),
        "fix_history": job.get("fix_history", []),
    }


@router.get("/drift/prerequisites")
async def drift_prerequisites() -> dict:
    """Check if prerequisites for drift detection are met."""
    ai_ok = is_ai_configured()
    ai_config = get_active_config()
    return {
        "ai_configured": ai_ok,
        "ai_provider": ai_config.provider.value if ai_config else None,
        "ready": ai_ok,
        "missing": []
        if ai_ok
        else ["AI provider not configured. Go to Settings to set one up."],
    }
