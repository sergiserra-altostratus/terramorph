"""VPC Network and Subnet discovery."""

import uuid

from google.cloud import compute_v1

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.network")


class NetworkDiscoverer(BaseDiscoverer):
    """Discovers VPC Networks and Subnets."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all VPC networks and subnets in a project."""
        resources = []

        try:
            # Discover VPC Networks
            networks_client = compute_v1.NetworksClient(credentials=self.credentials)
            request = compute_v1.ListNetworksRequest(project=project_id)

            for network in networks_client.list(request=request):
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.VPC_NETWORK,
                    name=network.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_network",
                    terraform_resource_name=self.sanitize_name(network.name),
                    terraform_import_id=f"projects/{project_id}/global/networks/{network.name}",
                    attributes={
                        "auto_create_subnetworks": network.auto_create_subnetworks,
                        "routing_mode": network.routing_config.routing_mode
                        if network.routing_config
                        else "REGIONAL",
                        "description": network.description or "",
                        "mtu": network.mtu if network.mtu else 1460,
                    },
                )
                resources.append(resource)

            # Discover Subnets
            subnets_client = compute_v1.SubnetworksClient(credentials=self.credentials)
            sub_request = compute_v1.AggregatedListSubnetworksRequest(project=project_id)

            for region, response in subnets_client.aggregated_list(request=sub_request):
                if response.subnetworks:
                    for subnet in response.subnetworks:
                        region_name = region.split("/")[-1]
                        resource = DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.SUBNET,
                            name=subnet.name,
                            project=project_id,
                            location=region_name,
                            terraform_resource_type="google_compute_subnetwork",
                            terraform_resource_name=self.sanitize_name(subnet.name),
                            terraform_import_id=(
                                f"projects/{project_id}/regions/{region_name}"
                                f"/subnetworks/{subnet.name}"
                            ),
                            attributes={
                                "ip_cidr_range": subnet.ip_cidr_range or "",
                                "network": subnet.network.split("/")[-1]
                                if subnet.network
                                else "",
                                "region": region_name,
                                "private_ip_google_access": subnet.private_ip_google_access,
                                "purpose": subnet.purpose if subnet.purpose else "PRIVATE",
                                "secondary_ip_ranges": [
                                    {
                                        "range_name": r.range_name,
                                        "ip_cidr_range": r.ip_cidr_range,
                                    }
                                    for r in (subnet.secondary_ip_ranges or [])
                                ],
                            },
                        )
                        resources.append(resource)

            logger.info(
                f"Discovered {len(resources)} network resources in {project_id}"
            )

        except Exception as e:
            logger.error(f"Error discovering networks in {project_id}: {e}")

        return resources
