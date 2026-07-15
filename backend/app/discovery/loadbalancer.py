"""Load Balancer (URL Maps / Forwarding Rules) discovery."""

import uuid

from google.cloud import compute_v1

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.loadbalancer")


class LoadBalancerDiscoverer(BaseDiscoverer):
    """Discovers HTTP(S) Load Balancers via global forwarding rules."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all load balancers in a project."""
        resources = []

        try:
            # Discover global forwarding rules (HTTP/HTTPS LBs)
            client = compute_v1.GlobalForwardingRulesClient(credentials=self.credentials)
            request = compute_v1.ListGlobalForwardingRulesRequest(project=project_id)

            for rule in client.list(request=request):
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.LOAD_BALANCER,
                    name=rule.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_global_forwarding_rule",
                    terraform_resource_name=self.sanitize_name(rule.name),
                    terraform_import_id=(
                        f"projects/{project_id}/global/forwardingRules/{rule.name}"
                    ),
                    attributes={
                        "target": rule.target.split("/")[-1] if rule.target else "",
                        "port_range": rule.port_range or "",
                        "ip_address": rule.I_p_address or "",
                        "ip_protocol": rule.I_p_protocol or "",
                        "load_balancing_scheme": rule.load_balancing_scheme or "",
                        "network": rule.network.split("/")[-1] if rule.network else "",
                        "description": rule.description or "",
                        "labels": dict(rule.labels) if rule.labels else {},
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} load balancers in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering load balancers in {project_id}: {e}")

        return resources
