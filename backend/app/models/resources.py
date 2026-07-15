"""Resource data models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Supported GCP resource types."""

    COMPUTE_INSTANCE = "compute_instance"
    VPC_NETWORK = "vpc_network"
    SUBNET = "subnet"
    GCS_BUCKET = "gcs_bucket"
    CLOUD_SQL = "cloud_sql"
    GKE_CLUSTER = "gke_cluster"


class ScopeType(str, Enum):
    """Discovery scope type."""

    PROJECT = "project"
    FOLDER = "folder"
    ORGANIZATION = "organization"


class ScopeConfig(BaseModel):
    """Discovery scope configuration."""

    type: ScopeType
    id: str = Field(description="The project ID, folder ID, or organization ID")


class DiscoveredResource(BaseModel):
    """A discovered GCP resource."""

    id: str = Field(description="Unique resource identifier")
    type: ResourceType
    name: str
    project: str
    location: str = Field(description="Zone, region, or 'global'")
    terraform_resource_type: str = Field(description="e.g., google_compute_instance")
    terraform_resource_name: str = Field(description="Sanitized name for Terraform")
    terraform_import_id: str = Field(description="ID for terraform import command")
    attributes: dict[str, Any] = Field(default_factory=dict)


class ResourceSummary(BaseModel):
    """Summary of discovered resources by type."""

    compute_instance: int = 0
    vpc_network: int = 0
    subnet: int = 0
    gcs_bucket: int = 0
    cloud_sql: int = 0
    gke_cluster: int = 0

    @property
    def total(self) -> int:
        return (
            self.compute_instance
            + self.vpc_network
            + self.subnet
            + self.gcs_bucket
            + self.cloud_sql
            + self.gke_cluster
        )
