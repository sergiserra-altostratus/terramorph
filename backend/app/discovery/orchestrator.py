"""Discovery orchestrator - coordinates all discoverers and manages jobs."""

import asyncio
import time
import uuid
from typing import Any

from google.auth.credentials import Credentials

from app.core.credentials import get_credentials
from app.core.logging import get_logger
from app.discovery.compute import ComputeDiscoverer
from app.discovery.gke import GKEDiscoverer
from app.discovery.network import NetworkDiscoverer
from app.discovery.sql import CloudSQLDiscoverer
from app.discovery.storage import StorageDiscoverer
from app.models.discovery import DiscoveryRequest, DiscoveryResult, DiscoveryStatus, JobProgress, JobStatus
from app.models.resources import DiscoveredResource, ResourceSummary, ResourceType, ScopeType

logger = get_logger("discovery.orchestrator")

# In-memory job storage
_jobs: dict[str, dict[str, Any]] = {}

# WebSocket subscribers for progress updates
_subscribers: dict[str, list[asyncio.Queue]] = {}


DISCOVERER_MAP = {
    ResourceType.COMPUTE_INSTANCE: ComputeDiscoverer,
    ResourceType.VPC_NETWORK: NetworkDiscoverer,
    ResourceType.GCS_BUCKET: StorageDiscoverer,
    ResourceType.CLOUD_SQL: CloudSQLDiscoverer,
    ResourceType.GKE_CLUSTER: GKEDiscoverer,
}


def subscribe(job_id: str) -> asyncio.Queue:
    """Subscribe to progress updates for a job."""
    if job_id not in _subscribers:
        _subscribers[job_id] = []
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers[job_id].append(queue)
    return queue


def unsubscribe(job_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from progress updates."""
    if job_id in _subscribers:
        _subscribers[job_id] = [q for q in _subscribers[job_id] if q is not queue]


async def _notify(job_id: str, progress: JobProgress) -> None:
    """Notify all subscribers of progress update."""
    if job_id in _subscribers:
        for queue in _subscribers[job_id]:
            await queue.put(progress.model_dump())


def get_job_status(job_id: str) -> DiscoveryStatus | None:
    """Get the current status of a discovery job."""
    job = _jobs.get(job_id)
    if not job:
        return None
    return DiscoveryStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        resources_found=len(job.get("resources", [])),
        error=job.get("error"),
    )


def get_job_results(job_id: str) -> DiscoveryResult | None:
    """Get the full results of a completed discovery job."""
    job = _jobs.get(job_id)
    if not job:
        return None

    resources: list[DiscoveredResource] = job.get("resources", [])
    summary = ResourceSummary(
        compute_instance=sum(1 for r in resources if r.type == ResourceType.COMPUTE_INSTANCE),
        vpc_network=sum(1 for r in resources if r.type == ResourceType.VPC_NETWORK),
        subnet=sum(1 for r in resources if r.type == ResourceType.SUBNET),
        gcs_bucket=sum(1 for r in resources if r.type == ResourceType.GCS_BUCKET),
        cloud_sql=sum(1 for r in resources if r.type == ResourceType.CLOUD_SQL),
        gke_cluster=sum(1 for r in resources if r.type == ResourceType.GKE_CLUSTER),
    )

    return DiscoveryResult(
        job_id=job_id,
        status=job["status"],
        resources=resources,
        summary=summary,
    )


async def _resolve_projects(scope_type: ScopeType, scope_id: str, credentials: Credentials) -> list[str]:
    """Resolve the list of project IDs to scan based on scope."""
    if scope_type == ScopeType.PROJECT:
        return [scope_id]

    from google.cloud import resourcemanager_v3

    client = resourcemanager_v3.ProjectsClient(credentials=credentials)

    if scope_type == ScopeType.ORGANIZATION:
        query = f"parent:organizations/{scope_id}"
    elif scope_type == ScopeType.FOLDER:
        query = f"parent:folders/{scope_id}"
    else:
        return [scope_id]

    request = resourcemanager_v3.SearchProjectsRequest(query=query)
    projects = []
    for project in client.search_projects(request=request):
        if project.state.name == "ACTIVE":
            projects.append(project.project_id)

    return projects


async def start_discovery(request: DiscoveryRequest) -> str:
    """Start a new discovery job.

    Returns:
        The job ID for tracking progress.
    """
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": JobStatus.PENDING,
        "progress": JobProgress(total=len(request.resource_types), completed=0),
        "resources": [],
        "created_at": time.time(),
        "error": None,
    }

    # Launch the discovery in the background
    asyncio.create_task(_run_discovery(job_id, request))

    return job_id


async def _run_discovery(job_id: str, request: DiscoveryRequest) -> None:
    """Execute the discovery process in the background."""
    job = _jobs[job_id]
    job["status"] = JobStatus.RUNNING

    try:
        credentials = get_credentials()
        projects = await _resolve_projects(
            request.scope.type, request.scope.id, credentials
        )

        total_types = len(request.resource_types)
        all_resources: list[DiscoveredResource] = []

        for idx, resource_type in enumerate(request.resource_types):
            discoverer_class = DISCOVERER_MAP.get(resource_type)
            if not discoverer_class:
                continue

            progress = JobProgress(
                total=total_types,
                completed=idx,
                current_type=resource_type.value,
                message=f"Discovering {resource_type.value}...",
            )
            job["progress"] = progress
            await _notify(job_id, progress)

            discoverer = discoverer_class(credentials)
            for project_id in projects:
                resources = await discoverer.discover(project_id)
                all_resources.extend(resources)

        job["resources"] = all_resources
        job["status"] = JobStatus.COMPLETED
        job["progress"] = JobProgress(
            total=total_types,
            completed=total_types,
            message=f"Discovery complete. Found {len(all_resources)} resources.",
        )
        await _notify(job_id, job["progress"])

        logger.info(f"Job {job_id} completed: {len(all_resources)} resources found")

    except Exception as e:
        job["status"] = JobStatus.FAILED
        job["error"] = str(e)
        job["progress"].message = f"Discovery failed: {str(e)}"
        await _notify(job_id, job["progress"])
        logger.error(f"Job {job_id} failed: {e}")


def cleanup_expired_jobs(ttl_seconds: int = 3600) -> int:
    """Remove expired jobs from memory.

    Returns:
        Number of jobs removed.
    """
    now = time.time()
    expired = [
        job_id
        for job_id, job in _jobs.items()
        if now - job.get("created_at", 0) > ttl_seconds
    ]
    for job_id in expired:
        del _jobs[job_id]
        _subscribers.pop(job_id, None)
    return len(expired)
