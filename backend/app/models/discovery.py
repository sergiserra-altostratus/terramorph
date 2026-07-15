"""Discovery request/response models."""

from enum import Enum

from pydantic import BaseModel, Field

from app.models.resources import DiscoveredResource, ResourceSummary, ResourceType, ScopeConfig


class JobStatus(str, Enum):
    """Discovery job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveryRequest(BaseModel):
    """Request to start resource discovery."""

    scope: ScopeConfig
    resource_types: list[ResourceType] = Field(
        default=[
            ResourceType.COMPUTE_INSTANCE,
            ResourceType.VPC_NETWORK,
            ResourceType.GCS_BUCKET,
            ResourceType.CLOUD_SQL,
            ResourceType.GKE_CLUSTER,
        ],
        description="Resource types to discover",
    )


class JobProgress(BaseModel):
    """Progress of a discovery job."""

    total: int = 0
    completed: int = 0
    current_type: str | None = None
    message: str = ""


class DiscoveryStatus(BaseModel):
    """Status response for a discovery job."""

    job_id: str
    status: JobStatus
    progress: JobProgress
    resources_found: int = 0
    error: str | None = None


class DiscoveryResult(BaseModel):
    """Full discovery results."""

    job_id: str
    status: JobStatus
    resources: list[DiscoveredResource] = Field(default_factory=list)
    summary: ResourceSummary = Field(default_factory=ResourceSummary)
