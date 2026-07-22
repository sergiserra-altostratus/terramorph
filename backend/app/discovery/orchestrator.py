"""Discovery orchestrator - coordinates all discoverers and manages jobs."""

import asyncio
import time
import uuid
from typing import Any

from google.auth.credentials import Credentials

from app.core.credentials import get_credentials
from app.core.exceptions import DiscoveryError
from app.core.logging import get_logger
from app.discovery.artifact_registry import ArtifactRegistryDiscoverer
from app.discovery.apigateway import APIGatewayDiscoverer
from app.discovery.armor import CloudArmorDiscoverer
from app.discovery.bigquery import BigQueryDiscoverer
from app.discovery.bigtable import BigtableDiscoverer
from app.discovery.cloudrun import CloudRunDiscoverer
from app.discovery.composer import ComposerDiscoverer
from app.discovery.compute import ComputeDiscoverer
from app.discovery.compute_disk import ComputeDiskDiscoverer
from app.discovery.compute_image import ComputeImageDiscoverer
from app.discovery.compute_reservation import ComputeReservationDiscoverer
from app.discovery.compute_route import ComputeRouteDiscoverer
from app.discovery.compute_snapshot import ComputeSnapshotDiscoverer
from app.discovery.custom_roles import CustomRolesDiscoverer
from app.discovery.dataflow import DataflowDiscoverer
from app.discovery.dns import CloudDNSDiscoverer
from app.discovery.dns_policy import DNSPolicyDiscoverer
from app.discovery.filestore import FilestoreDiscoverer
from app.discovery.firewall import FirewallDiscoverer
from app.discovery.functions import CloudFunctionsDiscoverer
from app.discovery.gke import GKEDiscoverer
from app.discovery.health_check import HealthCheckDiscoverer
from app.discovery.iam import IAMServiceAccountDiscoverer
from app.discovery.iam_bindings import IAMBindingsDiscoverer
from app.discovery.instance_group import InstanceGroupDiscoverer
from app.discovery.instance_template import InstanceTemplateDiscoverer
from app.discovery.kms import CloudKMSDiscoverer
from app.discovery.loadbalancer import LoadBalancerDiscoverer
from app.discovery.logging_sinks import LoggingSinksDiscoverer
from app.discovery.monitoring import MonitoringAlertsDiscoverer
from app.discovery.nat import CloudNATDiscoverer
from app.discovery.network import NetworkDiscoverer
from app.discovery.pubsub import PubSubDiscoverer
from app.discovery.redis import MemorystoreDiscoverer
from app.discovery.scheduler import CloudSchedulerDiscoverer
from app.discovery.secrets import SecretManagerDiscoverer
from app.discovery.spanner import SpannerDiscoverer
from app.discovery.sql import CloudSQLDiscoverer
from app.discovery.ssl_policy import SSLPolicyDiscoverer
from app.discovery.static_ip import StaticIPDiscoverer
from app.discovery.storage import StorageDiscoverer
from app.discovery.tasks import CloudTasksDiscoverer
from app.discovery.vertex_ai import VertexAIDiscoverer
from app.discovery.vpc_connector import VPCAccessConnectorDiscoverer
from app.discovery.vpn import VPNDiscoverer
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
    ResourceType.FIREWALL_RULE: FirewallDiscoverer,
    ResourceType.LOAD_BALANCER: LoadBalancerDiscoverer,
    ResourceType.CLOUD_RUN: CloudRunDiscoverer,
    ResourceType.CLOUD_FUNCTION: CloudFunctionsDiscoverer,
    ResourceType.PUBSUB_TOPIC: PubSubDiscoverer,
    ResourceType.PUBSUB_SUBSCRIPTION: PubSubDiscoverer,
    ResourceType.SERVICE_ACCOUNT: IAMServiceAccountDiscoverer,
    ResourceType.CLOUD_DNS: CloudDNSDiscoverer,
    ResourceType.MEMORYSTORE_REDIS: MemorystoreDiscoverer,
    ResourceType.IAM_BINDING: IAMBindingsDiscoverer,
    ResourceType.CUSTOM_ROLE: CustomRolesDiscoverer,
    ResourceType.BIGQUERY_DATASET: BigQueryDiscoverer,
    ResourceType.SECRET: SecretManagerDiscoverer,
    ResourceType.ARTIFACT_REGISTRY: ArtifactRegistryDiscoverer,
    ResourceType.KMS_KEYRING: CloudKMSDiscoverer,
    ResourceType.CLOUD_NAT: CloudNATDiscoverer,
    ResourceType.CLOUD_SCHEDULER: CloudSchedulerDiscoverer,
    ResourceType.SPANNER_INSTANCE: SpannerDiscoverer,
    ResourceType.FILESTORE: FilestoreDiscoverer,
    ResourceType.CLOUD_ARMOR: CloudArmorDiscoverer,
    ResourceType.VPN_GATEWAY: VPNDiscoverer,
    ResourceType.STATIC_IP: StaticIPDiscoverer,
    ResourceType.CLOUD_TASKS: CloudTasksDiscoverer,
    ResourceType.DATAFLOW_JOB: DataflowDiscoverer,
    ResourceType.COMPOSER: ComposerDiscoverer,
    ResourceType.API_GATEWAY: APIGatewayDiscoverer,
    ResourceType.LOGGING_SINK: LoggingSinksDiscoverer,
    ResourceType.MONITORING_ALERT: MonitoringAlertsDiscoverer,
    ResourceType.SSL_POLICY: SSLPolicyDiscoverer,
    ResourceType.INSTANCE_GROUP: InstanceGroupDiscoverer,
    ResourceType.BIGTABLE_INSTANCE: BigtableDiscoverer,
    ResourceType.COMPUTE_DISK: ComputeDiskDiscoverer,
    ResourceType.VERTEX_AI_ENDPOINT: VertexAIDiscoverer,
    ResourceType.COMPUTE_SNAPSHOT: ComputeSnapshotDiscoverer,
    ResourceType.INSTANCE_TEMPLATE: InstanceTemplateDiscoverer,
    ResourceType.COMPUTE_IMAGE: ComputeImageDiscoverer,
    ResourceType.COMPUTE_RESERVATION: ComputeReservationDiscoverer,
    ResourceType.DNS_POLICY: DNSPolicyDiscoverer,
    ResourceType.VPC_CONNECTOR: VPCAccessConnectorDiscoverer,
    ResourceType.COMPUTE_ROUTE: ComputeRouteDiscoverer,
    ResourceType.HEALTH_CHECK: HealthCheckDiscoverer,
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

    # Build summary dynamically from ResourceType enum
    summary_data = {}
    for rt in ResourceType:
        summary_data[rt.value] = sum(1 for r in resources if r.type == rt)
    summary = ResourceSummary(**summary_data)

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

    try:
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

        if not projects:
            logger.warning(f"No active projects found in {scope_type.value} '{scope_id}'. Check permissions: roles/browser or roles/resourcemanager.folderViewer required.")

        return projects

    except Exception as e:
        logger.error(f"Failed to resolve projects for {scope_type.value} '{scope_id}': {e}")
        raise DiscoveryError(
            f"Cannot list projects in {scope_type.value} '{scope_id}'. "
            f"Ensure you have 'roles/browser' or 'roles/resourcemanager.folderViewer' permission. "
            f"Error: {str(e)[:200]}"
        )


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

        if not projects:
            job["status"] = JobStatus.FAILED
            job["error"] = f"No projects found in {request.scope.type.value} '{request.scope.id}'. Check permissions."
            job["progress"].message = job["error"]
            await _notify(job_id, job["progress"])
            from app.services.persistence import update_job
            update_job(job_id, "failed", 0, job["error"])
            return

        total_types = len(request.resource_types)
        all_resources: list[DiscoveredResource] = []
        errors: list[str] = []

        for idx, resource_type in enumerate(request.resource_types):
            discoverer_class = DISCOVERER_MAP.get(resource_type)
            if not discoverer_class:
                continue

            progress = JobProgress(
                total=total_types,
                completed=idx,
                current_type=resource_type.value,
                message=f"Discovering {resource_type.value} ({len(projects)} project(s))...",
            )
            job["progress"] = progress
            await _notify(job_id, progress)

            discoverer = discoverer_class(credentials)
            for project_id in projects:
                try:
                    resources = await asyncio.wait_for(
                        discoverer.discover(project_id),
                        timeout=60.0,  # 60s timeout per resource type per project
                    )
                    all_resources.extend(resources)
                except asyncio.TimeoutError:
                    err_msg = f"Timeout discovering {resource_type.value} in {project_id} (>60s)"
                    logger.warning(err_msg)
                    errors.append(err_msg)
                except Exception as e:
                    err_msg = f"Error discovering {resource_type.value} in {project_id}: {str(e)[:100]}"
                    logger.warning(err_msg)
                    errors.append(err_msg)

        job["resources"] = all_resources
        job["status"] = JobStatus.COMPLETED
        completion_msg = f"Discovery complete. Found {len(all_resources)} resources."
        if errors:
            completion_msg += f" ({len(errors)} warning(s): some resource types failed)"
            job["error"] = "; ".join(errors[:5])  # Keep first 5 errors
        job["progress"] = JobProgress(
            total=total_types,
            completed=total_types,
            message=completion_msg,
        )
        await _notify(job_id, job["progress"])

        # Persist job completion to SQLite
        from app.services.persistence import update_job
        update_job(job_id, "completed", len(all_resources), f"{len(all_resources)} resources across {total_types} types")

        logger.info(f"Job {job_id} completed: {len(all_resources)} resources found")

    except Exception as e:
        job["status"] = JobStatus.FAILED
        error_msg = str(e)[:500]
        job["error"] = error_msg
        job["progress"].message = f"Discovery failed: {error_msg}"
        await _notify(job_id, job["progress"])

        from app.services.persistence import update_job
        update_job(job_id, "failed", 0, str(e))
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
