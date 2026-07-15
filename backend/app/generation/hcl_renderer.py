"""HCL template rendering engine using Jinja2."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.models.resources import DiscoveredResource, ResourceType

TEMPLATES_DIR = Path(__file__).parent / "templates"

RESOURCE_TYPE_FILE_MAP = {
    ResourceType.COMPUTE_INSTANCE: "compute.tf",
    ResourceType.VPC_NETWORK: "network.tf",
    ResourceType.SUBNET: "network.tf",
    ResourceType.GCS_BUCKET: "storage.tf",
    ResourceType.CLOUD_SQL: "sql.tf",
    ResourceType.GKE_CLUSTER: "gke.tf",
}

RESOURCE_TYPE_TEMPLATE_MAP = {
    ResourceType.COMPUTE_INSTANCE: "compute_instance.tf.j2",
    ResourceType.VPC_NETWORK: "vpc_network.tf.j2",
    ResourceType.SUBNET: "subnet.tf.j2",
    ResourceType.GCS_BUCKET: "gcs_bucket.tf.j2",
    ResourceType.CLOUD_SQL: "cloud_sql.tf.j2",
    ResourceType.GKE_CLUSTER: "gke_cluster.tf.j2",
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

    def render_all(self, resources: list[DiscoveredResource]) -> str:
        """Render all resources into a single file."""
        blocks = []
        for resource in resources:
            blocks.append(self.render_resource(resource))
        return "\n".join(blocks)

    def render_by_type(self, resources: list[DiscoveredResource]) -> dict[str, str]:
        """Render resources grouped by type into separate files.

        Returns:
            Dictionary mapping filename to HCL content.
        """
        grouped: dict[str, list[str]] = {}

        for resource in resources:
            filename = RESOURCE_TYPE_FILE_MAP.get(resource.type, "other.tf")
            if filename not in grouped:
                grouped[filename] = []
            grouped[filename].append(self.render_resource(resource))

        return {filename: "\n".join(blocks) for filename, blocks in grouped.items()}
