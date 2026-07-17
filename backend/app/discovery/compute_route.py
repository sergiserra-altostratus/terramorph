"""Compute route discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.compute_route")


class ComputeRouteDiscoverer(BaseDiscoverer):
    """Discovers custom network routes."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.RoutesClient(credentials=self.credentials)
            request = compute_v1.ListRoutesRequest(project=project_id)
            for route in client.list(request=request):
                # Skip default/system routes
                if route.name.startswith("default-route"):
                    continue
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.COMPUTE_ROUTE,
                    name=route.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_route",
                    terraform_resource_name=self.sanitize_name(route.name),
                    terraform_import_id=f"projects/{project_id}/global/routes/{route.name}",
                    attributes={
                        "network": route.network.split("/")[-1] if route.network else "",
                        "dest_range": route.dest_range or "",
                        "next_hop_gateway": route.next_hop_gateway.split("/")[-1] if route.next_hop_gateway else "",
                        "next_hop_ip": route.next_hop_ip or "",
                        "next_hop_instance": route.next_hop_instance.split("/")[-1] if route.next_hop_instance else "",
                        "priority": route.priority or 1000,
                        "tags": list(route.tags) if route.tags else [],
                    },
                ))
            logger.info(f"Discovered {len(resources)} routes in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering routes in {project_id}: {e}")
        return resources
