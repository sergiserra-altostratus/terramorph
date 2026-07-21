"""Discovery API endpoints."""

from fastapi import APIRouter, HTTPException

from app.core.exceptions import CredentialError
from app.discovery.orchestrator import get_job_results, get_job_status, start_discovery
from app.models.discovery import DiscoveryRequest, DiscoveryResult, DiscoveryStatus

router = APIRouter()


@router.post("/discovery/start")
async def start_discovery_job(request: DiscoveryRequest) -> dict:
    """Start a new resource discovery job."""
    from app.services.persistence import audit, record_job
    from app.core.validation import validate_gcp_scope_id

    # Validate scope ID before it reaches subprocess
    validate_gcp_scope_id(request.scope.type.value, request.scope.id)

    try:
        job_id = await start_discovery(request)
        record_job(job_id, "discovery", "gcp", "running", {"scope": request.scope.model_dump(), "types": [t.value for t in request.resource_types]})
        audit("discovery.started", "discovery", {"job_id": job_id, "scope_type": request.scope.type.value, "scope_id": request.scope.id})
        return {"job_id": job_id, "status": "running"}
    except CredentialError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start discovery: {str(e)}")


@router.get("/discovery/status/{job_id}", response_model=DiscoveryStatus)
async def get_discovery_status(job_id: str) -> DiscoveryStatus:
    """Get the status of a discovery job."""
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return status


@router.get("/discovery/results/{job_id}", response_model=DiscoveryResult)
async def get_discovery_results(job_id: str) -> DiscoveryResult:
    """Get the full results of a completed discovery job."""
    result = get_job_results(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return result
