"""Cloud NAT and Cloud Router discovery."""

import uuid

from google.cloud import compute_v1

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.nat")


class CloudNATDiscoverer(BaseDiscoverer):
    """Discovers Cloud Routers and Cloud NAT configurations."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Cloud Routers (with NAT config) in a project."""
        resources = []

        try:
            client = compute_v1.RoutersClient(credentials=self.credentials)
            request = compute_v1.AggregatedListRoutersRequest(project=project_id)

            for region, response in client.aggregated_list(request=request):
                if response.routers:
                    for router in response.routers:
                        region_name = region.split("/")[-1]

                        for nat in router.nats or []:
                            resource = DiscoveredResource(
                                id=str(uuid.uuid4()),
                                type=ResourceType.CLOUD_NAT,
                                name=nat.name,
                                project=project_id,
                                location=region_name,
                                terraform_resource_type="google_compute_router_nat",
                                terraform_resource_name=self.sanitize_name(nat.name),
                                terraform_import_id=(
                                    f"projects/{project_id}/regions/{region_name}"
                                    f"/routers/{router.name}/{nat.name}"
                                ),
                                attributes={
                                    "router": router.name,
                                    "region": region_name,
                                    "nat_ip_allocate_option": nat.nat_ip_allocate_option
                                    or "AUTO_ONLY",
                                    "source_subnetwork_ip_ranges_to_nat": (
                                        nat.source_subnetwork_ip_ranges_to_nat
                                        or "ALL_SUBNETWORKS_ALL_IP_RANGES"
                                    ),
                                    "min_ports_per_vm": nat.min_ports_per_vm or 64,
                                    "log_config_enabled": bool(nat.log_config),
                                },
                            )
                            resources.append(resource)

            logger.info(f"Discovered {len(resources)} Cloud NAT configs in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Cloud NAT in {project_id}: {e}")

        return resources
