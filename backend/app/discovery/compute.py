"""Compute Engine instance discovery."""

import uuid

from google.cloud import compute_v1

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.compute")


class ComputeDiscoverer(BaseDiscoverer):
    """Discovers Compute Engine instances."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Compute Engine instances in a project."""
        resources = []

        try:
            client = compute_v1.InstancesClient(credentials=self.credentials)
            request = compute_v1.AggregatedListInstancesRequest(project=project_id)

            for zone, response in client.aggregated_list(request=request):
                if response.instances:
                    for instance in response.instances:
                        zone_name = zone.split("/")[-1]
                        resource = DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.COMPUTE_INSTANCE,
                            name=instance.name,
                            project=project_id,
                            location=zone_name,
                            terraform_resource_type="google_compute_instance",
                            terraform_resource_name=self.sanitize_name(instance.name),
                            terraform_import_id=(
                                f"projects/{project_id}/zones/{zone_name}/instances/{instance.name}"
                            ),
                            attributes={
                                "machine_type": instance.machine_type.split("/")[-1]
                                if instance.machine_type
                                else "",
                                "zone": zone_name,
                                "status": instance.status,
                                "network_interfaces": [
                                    {
                                        "network": ni.network.split("/")[-1] if ni.network else "",
                                        "subnetwork": ni.subnetwork.split("/")[-1]
                                        if ni.subnetwork
                                        else "",
                                    }
                                    for ni in (instance.network_interfaces or [])
                                ],
                                "disks": [
                                    {
                                        "boot": disk.boot,
                                        "auto_delete": disk.auto_delete,
                                        "source": disk.source.split("/")[-1]
                                        if disk.source
                                        else "",
                                    }
                                    for disk in (instance.disks or [])
                                ],
                                "tags": list(instance.tags.items) if instance.tags else [],
                                "labels": dict(instance.labels) if instance.labels else {},
                                "metadata": {
                                    item.key: item.value
                                    for item in (instance.metadata.items or [])
                                }
                                if instance.metadata
                                else {},
                            },
                        )
                        resources.append(resource)

            logger.info(f"Discovered {len(resources)} compute instances in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering compute instances in {project_id}: {e}")

        return resources
