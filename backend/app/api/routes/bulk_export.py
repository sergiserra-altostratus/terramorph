"""Bulk Export discovery API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.bulk_export import (
    is_gcloud_available,
    start_bulk_export,
    get_bulk_job_status,
    get_bulk_job_results,
    BULK_EXPORT_RESOURCE_TYPES,
)

router = APIRouter()


class BulkExportRequest(BaseModel):
    """Request to start bulk export discovery."""

    project_id: str = Field(description="GCP project ID")
    resource_types: list[str] | None = Field(
        default=None,
        description="Resource types to export. If null, exports all supported types.",
    )


@router.get("/bulk-export/check-api/{project_id}")
async def check_cloud_asset_api(project_id: str) -> dict:
    """Check if Cloud Asset API is enabled for the given project.

    Uses Python SDK (not gcloud CLI) for authentication compatibility.
    """
    try:
        from google.auth import default
        from googleapiclient.discovery import build

        credentials, _ = default()
        service = build("serviceusage", "v1", credentials=credentials)
        name = f"projects/{project_id}/services/cloudasset.googleapis.com"
        result = service.services().get(name=name).execute()

        is_enabled = result.get("state") == "ENABLED"
        return {
            "enabled": is_enabled,
            "project_id": project_id,
            "message": "Cloud Asset API is enabled. Bulk Export is ready."
            if is_enabled
            else f"Cloud Asset API is NOT enabled. Enable it with: gcloud services enable cloudasset.googleapis.com --project={project_id}",
        }
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "permission" in error_msg.lower():
            return {
                "enabled": False,
                "project_id": project_id,
                "error": f"Permission denied. Ensure your account has serviceusage.services.get permission on project '{project_id}'.",
            }
        elif "404" in error_msg or "not found" in error_msg.lower():
            return {
                "enabled": False,
                "project_id": project_id,
                "error": f"Project '{project_id}' not found or you don't have access.",
            }
        return {
            "enabled": False,
            "project_id": project_id,
            "error": f"Unable to check API status: {error_msg[:200]}",
        }


@router.get("/bulk-export/available")
async def bulk_export_info() -> dict:
    """Check if bulk export is available and list supported types."""
    return {
        "available": is_gcloud_available(),
        "resource_types": BULK_EXPORT_RESOURCE_TYPES,
        "total_types": len(BULK_EXPORT_RESOURCE_TYPES),
    }


@router.post("/bulk-export/start")
async def start_bulk_export_job(request: BulkExportRequest) -> dict:
    """Start a bulk export discovery job."""
    from app.core.validation import validate_gcp_project_id

    if not is_gcloud_available():
        raise HTTPException(
            status_code=503,
            detail="gcloud CLI is not available. Bulk Export requires the Google Cloud SDK installed in the backend.",
        )

    # Validate project ID before it reaches gcloud subprocess
    validate_gcp_project_id(request.project_id)

    job_id = await start_bulk_export(
        project_id=request.project_id.strip(),
        resource_types=request.resource_types,
    )

    return {"job_id": job_id, "status": "running", "mode": "bulk_export"}


@router.get("/bulk-export/status/{job_id}")
async def bulk_export_status(job_id: str) -> dict:
    """Get bulk export job status."""
    job = get_bulk_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"].model_dump() if hasattr(job["progress"], "model_dump") else job["progress"],
        "resources_found": len(job.get("resources", [])),
        "error": job.get("error"),
    }


@router.get("/bulk-export/results/{job_id}")
async def bulk_export_results(job_id: str) -> dict:
    """Get bulk export full results including generated TF files."""
    result = get_bulk_job_results(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return result
