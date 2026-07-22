"""HCL template rendering engine using Jinja2."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.models.resources import DiscoveredResource, ResourceType

TEMPLATES_DIR = Path(__file__).parent / "templates"
MODULES_DIR = Path(__file__).parent / "templates" / "modules"

# Module template map - resource types that have official module equivalents
MODULE_TEMPLATE_MAP = {
    ResourceType.COMPUTE_INSTANCE: "modules/compute_instance.tf.j2",
    ResourceType.VPC_NETWORK: "modules/vpc_network.tf.j2",
    ResourceType.GCS_BUCKET: "modules/gcs_bucket.tf.j2",
    ResourceType.CLOUD_SQL: "modules/cloud_sql.tf.j2",
    ResourceType.GKE_CLUSTER: "modules/gke_cluster.tf.j2",
    ResourceType.CLOUD_RUN: "modules/cloud_run.tf.j2",
    ResourceType.SERVICE_ACCOUNT: "modules/service_account.tf.j2",
    ResourceType.CLOUD_NAT: "modules/cloud_nat.tf.j2",
    ResourceType.CLOUD_DNS: "modules/cloud_dns.tf.j2",
    ResourceType.VPN_GATEWAY: "modules/vpn.tf.j2",
    ResourceType.IAM_BINDING: "modules/iam_binding.tf.j2",
    ResourceType.KMS_KEYRING: "modules/kms.tf.j2",
    ResourceType.PUBSUB_TOPIC: "modules/pubsub.tf.j2",
    ResourceType.BIGQUERY_DATASET: "modules/bigquery.tf.j2",
    ResourceType.MEMORYSTORE_REDIS: "modules/memorystore.tf.j2",
    ResourceType.LOAD_BALANCER: "modules/load_balancer.tf.j2",
    ResourceType.LOGGING_SINK: "modules/log_export.tf.j2",
    ResourceType.STATIC_IP: "modules/address.tf.j2",
    ResourceType.CLOUD_SCHEDULER: "modules/scheduled_function.tf.j2",
    ResourceType.MONITORING_ALERT: "modules/monitoring.tf.j2",
}

RESOURCE_TYPE_FILE_MAP = {
    ResourceType.COMPUTE_INSTANCE: "compute.tf",
    ResourceType.VPC_NETWORK: "network.tf",
    ResourceType.SUBNET: "network.tf",
    ResourceType.GCS_BUCKET: "storage.tf",
    ResourceType.CLOUD_SQL: "sql.tf",
    ResourceType.GKE_CLUSTER: "gke.tf",
    ResourceType.FIREWALL_RULE: "firewall.tf",
    ResourceType.LOAD_BALANCER: "loadbalancer.tf",
    ResourceType.CLOUD_RUN: "cloudrun.tf",
    ResourceType.CLOUD_FUNCTION: "functions.tf",
    ResourceType.PUBSUB_TOPIC: "pubsub.tf",
    ResourceType.PUBSUB_SUBSCRIPTION: "pubsub.tf",
    ResourceType.SERVICE_ACCOUNT: "iam.tf",
    ResourceType.CLOUD_DNS: "dns.tf",
    ResourceType.MEMORYSTORE_REDIS: "redis.tf",
    ResourceType.IAM_BINDING: "iam.tf",
    ResourceType.CUSTOM_ROLE: "iam.tf",
    ResourceType.BIGQUERY_DATASET: "bigquery.tf",
    ResourceType.SECRET: "secrets.tf",
    ResourceType.ARTIFACT_REGISTRY: "artifact_registry.tf",
    ResourceType.KMS_KEYRING: "kms.tf",
    ResourceType.CLOUD_NAT: "nat.tf",
    ResourceType.CLOUD_SCHEDULER: "scheduler.tf",
    ResourceType.SPANNER_INSTANCE: "spanner.tf",
    ResourceType.FILESTORE: "filestore.tf",
    ResourceType.CLOUD_ARMOR: "armor.tf",
    ResourceType.VPN_GATEWAY: "vpn.tf",
    ResourceType.STATIC_IP: "addresses.tf",
    ResourceType.CLOUD_TASKS: "tasks.tf",
    ResourceType.DATAFLOW_JOB: "dataflow.tf",
    ResourceType.COMPOSER: "composer.tf",
    ResourceType.API_GATEWAY: "apigateway.tf",
    ResourceType.LOGGING_SINK: "logging.tf",
    ResourceType.MONITORING_ALERT: "monitoring.tf",
    ResourceType.SSL_POLICY: "ssl.tf",
    ResourceType.INSTANCE_GROUP: "instance_groups.tf",
    ResourceType.BIGTABLE_INSTANCE: "bigtable.tf",
    ResourceType.COMPUTE_DISK: "disks.tf",
    ResourceType.VERTEX_AI_ENDPOINT: "vertex_ai.tf",
    ResourceType.COMPUTE_SNAPSHOT: "snapshots.tf",
    ResourceType.INSTANCE_TEMPLATE: "instance_templates.tf",
    ResourceType.COMPUTE_IMAGE: "images.tf",
    ResourceType.COMPUTE_RESERVATION: "reservations.tf",
    ResourceType.DNS_POLICY: "dns.tf",
    ResourceType.VPC_CONNECTOR: "vpc_connectors.tf",
    ResourceType.COMPUTE_ROUTE: "routes.tf",
    ResourceType.HEALTH_CHECK: "healthchecks.tf",
}

RESOURCE_TYPE_TEMPLATE_MAP = {
    ResourceType.COMPUTE_INSTANCE: "compute_instance.tf.j2",
    ResourceType.VPC_NETWORK: "vpc_network.tf.j2",
    ResourceType.SUBNET: "subnet.tf.j2",
    ResourceType.GCS_BUCKET: "gcs_bucket.tf.j2",
    ResourceType.CLOUD_SQL: "cloud_sql.tf.j2",
    ResourceType.GKE_CLUSTER: "gke_cluster.tf.j2",
    ResourceType.FIREWALL_RULE: "firewall.tf.j2",
    ResourceType.LOAD_BALANCER: "load_balancer.tf.j2",
    ResourceType.CLOUD_RUN: "cloud_run.tf.j2",
    ResourceType.CLOUD_FUNCTION: "cloud_function.tf.j2",
    ResourceType.PUBSUB_TOPIC: "pubsub_topic.tf.j2",
    ResourceType.PUBSUB_SUBSCRIPTION: "pubsub_subscription.tf.j2",
    ResourceType.SERVICE_ACCOUNT: "service_account.tf.j2",
    ResourceType.CLOUD_DNS: "dns_zone.tf.j2",
    ResourceType.MEMORYSTORE_REDIS: "redis.tf.j2",
    ResourceType.IAM_BINDING: "iam_binding.tf.j2",
    ResourceType.CUSTOM_ROLE: "custom_role.tf.j2",
    ResourceType.BIGQUERY_DATASET: "bigquery_dataset.tf.j2",
    ResourceType.SECRET: "secret.tf.j2",
    ResourceType.ARTIFACT_REGISTRY: "artifact_registry.tf.j2",
    ResourceType.KMS_KEYRING: "kms_keyring.tf.j2",
    ResourceType.CLOUD_NAT: "cloud_nat.tf.j2",
    ResourceType.CLOUD_SCHEDULER: "cloud_scheduler.tf.j2",
    ResourceType.SPANNER_INSTANCE: "spanner.tf.j2",
    ResourceType.FILESTORE: "filestore.tf.j2",
    ResourceType.CLOUD_ARMOR: "cloud_armor.tf.j2",
    ResourceType.VPN_GATEWAY: "vpn_gateway.tf.j2",
    ResourceType.STATIC_IP: "static_ip.tf.j2",
    ResourceType.CLOUD_TASKS: "cloud_tasks.tf.j2",
    ResourceType.DATAFLOW_JOB: "dataflow.tf.j2",
    ResourceType.COMPOSER: "composer.tf.j2",
    ResourceType.API_GATEWAY: "api_gateway.tf.j2",
    ResourceType.LOGGING_SINK: "logging_sink.tf.j2",
    ResourceType.MONITORING_ALERT: "monitoring_alert.tf.j2",
    ResourceType.SSL_POLICY: "ssl_policy.tf.j2",
    ResourceType.INSTANCE_GROUP: "instance_group.tf.j2",
    ResourceType.BIGTABLE_INSTANCE: "bigtable.tf.j2",
    ResourceType.COMPUTE_DISK: "compute_disk.tf.j2",
    ResourceType.VERTEX_AI_ENDPOINT: "vertex_ai.tf.j2",
    ResourceType.COMPUTE_SNAPSHOT: "compute_snapshot.tf.j2",
    ResourceType.INSTANCE_TEMPLATE: "instance_template.tf.j2",
    ResourceType.COMPUTE_IMAGE: "compute_image.tf.j2",
    ResourceType.COMPUTE_RESERVATION: "compute_reservation.tf.j2",
    ResourceType.DNS_POLICY: "dns_policy.tf.j2",
    ResourceType.VPC_CONNECTOR: "vpc_connector.tf.j2",
    ResourceType.COMPUTE_ROUTE: "compute_route.tf.j2",
    ResourceType.HEALTH_CHECK: "health_check.tf.j2",
}


class HCLRenderer:
    """Renders Terraform HCL from discovered resources using Jinja2 templates."""

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render_provider(self, project_id: str) -> str:
        """Render the provider.tf file."""
        template = self.env.get_template("provider.tf.j2")
        return template.render(project_id=project_id)

    def render_backend(self, bucket: str, prefix: str) -> str:
        """Render the backend.tf file for GCS remote state.

        Args:
            bucket: GCS bucket name for storing tfstate.
            prefix: Path prefix within the bucket.

        Returns:
            Rendered backend.tf content.
        """
        template = self.env.get_template("backend.tf.j2")
        return template.render(bucket=bucket, prefix=prefix)

    def render_resource(self, resource: DiscoveredResource) -> str:
        """Render a single resource to HCL."""
        template_name = RESOURCE_TYPE_TEMPLATE_MAP.get(resource.type)
        if not template_name:
            return f"# Unsupported resource type: {resource.type}\n"

        template = self.env.get_template(template_name)
        return template.render(resource=resource, attrs=resource.attributes)

    def _deduplicate_names(self, resources: list[DiscoveredResource]) -> list[DiscoveredResource]:
        """Ensure all terraform_resource_name values are unique per type.

        If duplicates are found, appends a counter suffix.
        """
        seen: dict[str, int] = {}
        for resource in resources:
            key = f"{resource.terraform_resource_type}.{resource.terraform_resource_name}"
            if key in seen:
                seen[key] += 1
                resource.terraform_resource_name = f"{resource.terraform_resource_name}_{seen[key]}"
            else:
                seen[key] = 0
        return resources

    def render_all(self, resources: list[DiscoveredResource]) -> str:
        """Render all resources into a single file."""
        resources = self._deduplicate_names(resources)
        blocks = []
        for resource in resources:
            blocks.append(self.render_resource(resource))
        return "\n".join(blocks)

    def render_by_type(self, resources: list[DiscoveredResource]) -> dict[str, str]:
        """Render resources grouped by type into separate files.

        Returns:
            Dictionary mapping filename to HCL content.
        """
        resources = self._deduplicate_names(resources)
        grouped: dict[str, list[str]] = {}

        for resource in resources:
            filename = RESOURCE_TYPE_FILE_MAP.get(resource.type, "other.tf")
            if filename not in grouped:
                grouped[filename] = []
            grouped[filename].append(self.render_resource(resource))

        return {filename: "\n".join(blocks) for filename, blocks in grouped.items()}

    def render_resource_as_module(self, resource: DiscoveredResource) -> str:
        """Render a single resource using module template.

        Falls back to flat resource if no module template exists for the type.
        """
        template_name = MODULE_TEMPLATE_MAP.get(resource.type)
        if not template_name:
            # Fallback to flat resource for types without module support
            return self.render_resource(resource)

        template = self.env.get_template(template_name)
        return template.render(resource=resource, attrs=resource.attributes)

    def render_all_as_modules(self, resources: list[DiscoveredResource]) -> str:
        """Render all resources as modules into a single file."""
        resources = self._deduplicate_names(resources)
        blocks = []
        for resource in resources:
            blocks.append(self.render_resource_as_module(resource))
        return "\n".join(blocks)

    def render_by_type_as_modules(self, resources: list[DiscoveredResource]) -> dict[str, str]:
        """Render resources as modules grouped by type into separate files.

        Returns:
            Dictionary mapping filename to HCL content.
        """
        resources = self._deduplicate_names(resources)
        grouped: dict[str, list[str]] = {}

        for resource in resources:
            filename = RESOURCE_TYPE_FILE_MAP.get(resource.type, "other.tf")
            if filename not in grouped:
                grouped[filename] = []
            grouped[filename].append(self.render_resource_as_module(resource))

        return {filename: "\n".join(blocks) for filename, blocks in grouped.items()}
