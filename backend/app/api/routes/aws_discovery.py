"""AWS Discovery API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.discovery.aws.orchestrator import (
    start_aws_discovery,
    get_aws_job_status,
    get_aws_job_results,
    AWS_DISCOVERER_MAP,
)
from app.models.resources import ResourceType
from app.services.aws_credentials import is_aws_configured

router = APIRouter()

AWS_ALL_TYPES = [rt for rt in AWS_DISCOVERER_MAP.keys()]


class AWSDiscoveryRequest(BaseModel):
    """Request to start AWS discovery."""

    resource_types: list[str] = Field(
        default=[],
        description="AWS resource types to discover. Empty = all.",
    )


@router.get("/aws/discovery/types")
async def get_aws_resource_types() -> dict:
    """Get available AWS resource types for discovery."""
    return {
        "types": [{"value": rt.value, "label": rt.value.replace("aws_", "").replace("_", " ").title()} for rt in AWS_ALL_TYPES],
        "total": len(AWS_ALL_TYPES),
    }


@router.post("/aws/discovery/start")
async def start_aws_discovery_job(request: AWSDiscoveryRequest) -> dict:
    """Start AWS resource discovery."""
    if not is_aws_configured():
        raise HTTPException(status_code=412, detail="AWS credentials not configured. Go to Settings to configure them.")

    if request.resource_types:
        types = [ResourceType(t) for t in request.resource_types if t.startswith("aws_")]
    else:
        types = AWS_ALL_TYPES

    try:
        job_id = await start_aws_discovery(types)
        return {"job_id": job_id, "status": "running", "provider": "aws"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aws/discovery/status/{job_id}")
async def aws_discovery_status(job_id: str) -> dict:
    """Get AWS discovery job status."""
    job = get_aws_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"].model_dump() if hasattr(job["progress"], "model_dump") else job["progress"],
        "resources_found": len(job.get("resources", [])),
    }


@router.get("/aws/discovery/results/{job_id}")
async def aws_discovery_results(job_id: str) -> dict:
    """Get AWS discovery results."""
    result = get_aws_job_results(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return result
