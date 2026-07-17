"""Compute persistent disk discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.compute_disk")


class ComputeDiskDiscoverer(BaseDiscoverer):
    """Discovers persistent disks."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.DisksClient(credentials=self.credentials)
            request = compute_v1.AggregatedListDisksRequest(project=project_id)
            for zone, response in client.aggregated_list(request=request):
                if response.disks:
                    for disk in response.disks:
                        zone_name = zone.split("/")[-1]
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.COMPUTE_DISK,
                            name=disk.name,
                            project=project_id,
                            location=zone_name,
                            terraform_resource_type="google_compute_disk",
                            terraform_resource_name=self.sanitize_name(disk.name),
                            terraform_import_id=f"projects/{project_id}/zones/{zone_name}/disks/{disk.name}",
                            attributes={
                                "zone": zone_name,
                                "type": disk.type_.split("/")[-1] if disk.type_ else "pd-standard",
                                "size": disk.size_gb or 10,
                                "image": disk.source_image.split("/")[-1] if disk.source_image else "",
                                "labels": dict(disk.labels) if disk.labels else {},
                            },
                        ))
            logger.info(f"Discovered {len(resources)} disks in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering disks in {project_id}: {e}")
        return resources
