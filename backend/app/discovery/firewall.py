"""Firewall Rules discovery."""

import uuid

from google.cloud import compute_v1

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.firewall")


class FirewallDiscoverer(BaseDiscoverer):
    """Discovers VPC Firewall Rules."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all firewall rules in a project."""
        resources = []

        try:
            client = compute_v1.FirewallsClient(credentials=self.credentials)
            request = compute_v1.ListFirewallsRequest(project=project_id)

            for rule in client.list(request=request):
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.FIREWALL_RULE,
                    name=rule.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_firewall",
                    terraform_resource_name=self.sanitize_name(rule.name),
                    terraform_import_id=f"projects/{project_id}/global/firewalls/{rule.name}",
                    attributes={
                        "network": rule.network.split("/")[-1] if rule.network else "default",
                        "direction": rule.direction if rule.direction else "INGRESS",
                        "priority": rule.priority if rule.priority else 1000,
                        "source_ranges": list(rule.source_ranges) if rule.source_ranges else [],
                        "destination_ranges": list(rule.destination_ranges)
                        if rule.destination_ranges
                        else [],
                        "source_tags": list(rule.source_tags) if rule.source_tags else [],
                        "target_tags": list(rule.target_tags) if rule.target_tags else [],
                        "allowed": [
                            {
                                "protocol": a.I_p_protocol,
                                "ports": list(a.ports) if a.ports else [],
                            }
                            for a in (rule.allowed or [])
                        ],
                        "denied": [
                            {
                                "protocol": d.I_p_protocol,
                                "ports": list(d.ports) if d.ports else [],
                            }
                            for d in (rule.denied or [])
                        ],
                        "disabled": rule.disabled if rule.disabled else False,
                        "description": rule.description or "",
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} firewall rules in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering firewall rules in {project_id}: {e}")

        return resources
