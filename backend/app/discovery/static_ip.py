"""Static IP address discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.static_ip")


class StaticIPDiscoverer(BaseDiscoverer):
    """Discovers reserved static IP addresses (global and regional)."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            # Global addresses
            global_client = compute_v1.GlobalAddressesClient(credentials=self.credentials)
            for addr in global_client.list(project=project_id):
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.STATIC_IP,
                    name=addr.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_global_address",
                    terraform_resource_name=self.sanitize_name(addr.name),
                    terraform_import_id=f"projects/{project_id}/global/addresses/{addr.name}",
                    attributes={
                        "address": addr.address or "",
                        "address_type": addr.address_type or "EXTERNAL",
                        "purpose": addr.purpose or "",
                        "ip_version": addr.ip_version or "IPV4",
                        "description": addr.description or "",
                    },
                )
                resources.append(resource)

            # Regional addresses
            regional_client = compute_v1.AddressesClient(credentials=self.credentials)
            request = compute_v1.AggregatedListAddressesRequest(project=project_id)
            for region, response in regional_client.aggregated_list(request=request):
                if response.addresses:
                    for addr in response.addresses:
                        region_name = region.split("/")[-1]
                        resource = DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.STATIC_IP,
                            name=addr.name,
                            project=project_id,
                            location=region_name,
                            terraform_resource_type="google_compute_address",
                            terraform_resource_name=self.sanitize_name(f"{region_name}_{addr.name}"),
                            terraform_import_id=f"projects/{project_id}/regions/{region_name}/addresses/{addr.name}",
                            attributes={
                                "address": addr.address or "",
                                "address_type": addr.address_type or "EXTERNAL",
                                "region": region_name,
                                "purpose": addr.purpose or "",
                                "description": addr.description or "",
                            },
                        )
                        resources.append(resource)
            logger.info(f"Discovered {len(resources)} static IPs in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering static IPs in {project_id}: {e}")
        return resources
