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
    FIREWALL_RULE = "firewall_rule"
    LOAD_BALANCER = "load_balancer"
    CLOUD_RUN = "cloud_run"
    CLOUD_FUNCTION = "cloud_function"
    PUBSUB_TOPIC = "pubsub_topic"
    PUBSUB_SUBSCRIPTION = "pubsub_subscription"
    SERVICE_ACCOUNT = "service_account"
    CLOUD_DNS = "cloud_dns"
    MEMORYSTORE_REDIS = "memorystore_redis"
    IAM_BINDING = "iam_binding"
    CUSTOM_ROLE = "custom_role"
    BIGQUERY_DATASET = "bigquery_dataset"
    SECRET = "secret"
    ARTIFACT_REGISTRY = "artifact_registry"
    KMS_KEYRING = "kms_keyring"
    CLOUD_NAT = "cloud_nat"
    CLOUD_SCHEDULER = "cloud_scheduler"
    SPANNER_INSTANCE = "spanner_instance"
    FILESTORE = "filestore"
    CLOUD_ARMOR = "cloud_armor"
    VPN_GATEWAY = "vpn_gateway"
    STATIC_IP = "static_ip"
    CLOUD_TASKS = "cloud_tasks"
    DATAFLOW_JOB = "dataflow_job"
    COMPOSER = "composer"
    API_GATEWAY = "api_gateway"
    LOGGING_SINK = "logging_sink"
    MONITORING_ALERT = "monitoring_alert"
    SSL_POLICY = "ssl_policy"
    INSTANCE_GROUP = "instance_group"
    BIGTABLE_INSTANCE = "bigtable_instance"
    COMPUTE_DISK = "compute_disk"
    VERTEX_AI_ENDPOINT = "vertex_ai_endpoint"
    COMPUTE_SNAPSHOT = "compute_snapshot"
    INSTANCE_TEMPLATE = "instance_template"
    COMPUTE_IMAGE = "compute_image"
    COMPUTE_RESERVATION = "compute_reservation"
    DNS_POLICY = "dns_policy"
    VPC_CONNECTOR = "vpc_connector"
    COMPUTE_ROUTE = "compute_route"
    HEALTH_CHECK = "health_check"


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
    firewall_rule: int = 0
    load_balancer: int = 0
    cloud_run: int = 0
    cloud_function: int = 0
    pubsub_topic: int = 0
    pubsub_subscription: int = 0
    service_account: int = 0
    cloud_dns: int = 0
    memorystore_redis: int = 0
    iam_binding: int = 0
    custom_role: int = 0
    bigquery_dataset: int = 0
    secret: int = 0
    artifact_registry: int = 0
    kms_keyring: int = 0
    cloud_nat: int = 0
    cloud_scheduler: int = 0
    spanner_instance: int = 0
    filestore: int = 0
    cloud_armor: int = 0
    vpn_gateway: int = 0
    static_ip: int = 0
    cloud_tasks: int = 0
    dataflow_job: int = 0
    composer: int = 0
    api_gateway: int = 0
    logging_sink: int = 0
    monitoring_alert: int = 0
    ssl_policy: int = 0
    instance_group: int = 0
    bigtable_instance: int = 0
    compute_disk: int = 0
    vertex_ai_endpoint: int = 0
    compute_snapshot: int = 0
    instance_template: int = 0
    compute_image: int = 0
    compute_reservation: int = 0
    dns_policy: int = 0
    vpc_connector: int = 0
    compute_route: int = 0
    health_check: int = 0

    @property
    def total(self) -> int:
        return sum(
            getattr(self, field)
            for field in self.model_fields
        )
