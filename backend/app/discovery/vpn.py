"""Cloud VPN gateway and tunnel discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.vpn")


class VPNDiscoverer(BaseDiscoverer):
    """Discovers HA VPN Gateways."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.VpnGatewaysClient(credentials=self.credentials)
            request = compute_v1.AggregatedListVpnGatewaysRequest(project=project_id)

            for region, response in client.aggregated_list(request=request):
                if response.vpn_gateways:
                    for gw in response.vpn_gateways:
                        region_name = region.split("/")[-1]
                        resource = DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.VPN_GATEWAY,
                            name=gw.name,
                            project=project_id,
                            location=region_name,
                            terraform_resource_type="google_compute_ha_vpn_gateway",
                            terraform_resource_name=self.sanitize_name(gw.name),
                            terraform_import_id=f"projects/{project_id}/regions/{region_name}/vpnGateways/{gw.name}",
                            attributes={
                                "region": region_name,
                                "network": gw.network.split("/")[-1] if gw.network else "",
                                "stack_type": gw.stack_type if hasattr(gw, 'stack_type') else "IPV4_ONLY",
                            },
                        )
                        resources.append(resource)
            logger.info(f"Discovered {len(resources)} VPN gateways in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering VPN in {project_id}: {e}")
        return resources
