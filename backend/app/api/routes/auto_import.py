"""Auto Import API endpoints.

Upload .tf files → auto-generate import.tf → execute import → report drift.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_settings import is_ai_configured
from app.services.auto_import import (
    start_auto_import,
    get_auto_import_job,
    cancel_auto_import_job,
    set_drift_decision,
)

router = APIRouter()


class AutoImportRequest(BaseModel):
    """Request to start auto-import."""
    tf_files: dict[str, str] = Field(description="Dict of filename → HCL content. Must include backend.tf.")


class DriftDecisionRequest(BaseModel):
    """User's decision about detected drift."""
    decision: str = Field(description="One of: 'fix', 'download', 'ignore'")


@router.post("/auto-import/start")
async def start_auto_import_job(request: AutoImportRequest) -> dict:
    """Start an auto-import job.

    Validates that backend.tf is present, then runs the full import flow.
    """
    if not is_ai_configured():
        raise HTTPException(status_code=412, detail="AI provider not configured. Go to Settings.")

    if not request.tf_files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # Validate backend.tf is present
    has_backend = any(
        f.lower() == "backend.tf" for f in request.tf_files.keys()
    )
    if not has_backend:
        raise HTTPException(
            status_code=400,
            detail="backend.tf is required. Please upload your backend.tf file to configure the remote state.",
        )

    # Validate at least one resource file
    resource_files = [f for f in request.tf_files.keys() if f != "backend.tf"]
    if not resource_files:
        raise HTTPException(status_code=400, detail="No resource files provided. Upload at least one .tf file with resources.")

    job_id = await start_auto_import(tf_files=request.tf_files)
    return {"job_id": job_id, "status": "running"}


@router.get("/auto-import/status/{job_id}")
async def auto_import_status(job_id: str) -> dict:
    """Get auto-import job status."""
    job = get_auto_import_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "phase": job.get("phase"),
        "progress": job.get("progress"),
        "awaiting_decision": job.get("awaiting_decision", False),
        "error": job.get("error"),
    }


@router.get("/auto-import/results/{job_id}")
async def auto_import_results(job_id: str) -> dict:
    """Get auto-import results."""
    job = get_auto_import_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job["status"] == "running":
        raise HTTPException(status_code=409, detail="Job still running.")
    return {
        "job_id": job_id,
        "status": job["status"],
        "result": job.get("result"),
        "error": job.get("error"),
    }


@router.post("/auto-import/decision/{job_id}")
async def auto_import_decision(job_id: str, request: DriftDecisionRequest) -> dict:
    """Submit drift decision for an auto-import job."""
    if request.decision not in ("fix", "download", "ignore"):
        raise HTTPException(status_code=400, detail="Decision must be 'fix', 'download', or 'ignore'.")

    success = set_drift_decision(job_id, request.decision)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or not awaiting decision.")

    return {"job_id": job_id, "decision": request.decision, "message": "Decision received."}


@router.post("/auto-import/cancel/{job_id}")
async def cancel_auto_import(job_id: str) -> dict:
    """Cancel a running auto-import job."""
    success = cancel_auto_import_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or not running.")
    return {"job_id": job_id, "status": "cancelling"}
