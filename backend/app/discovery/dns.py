"""Cloud DNS managed zones discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.dns")


class CloudDNSDiscoverer(BaseDiscoverer):
    """Discovers Cloud DNS managed zones."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all DNS managed zones in a project."""
        resources = []

        try:
            service = build("dns", "v1", credentials=self.credentials)
            request = service.managedZones().list(project=project_id)
            response = request.execute()

            for zone in response.get("managedZones", []):
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_DNS,
                    name=zone["name"],
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_dns_managed_zone",
                    terraform_resource_name=self.sanitize_name(zone["name"]),
                    terraform_import_id=f"projects/{project_id}/managedZones/{zone['name']}",
                    attributes={
                        "dns_name": zone.get("dnsName", ""),
                        "description": zone.get("description", ""),
                        "visibility": zone.get("visibility", "public"),
                        "dnssec_state": zone.get("dnssecConfig", {}).get("state", "off"),
                        "labels": zone.get("labels", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} DNS zones in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering DNS zones in {project_id}: {e}")

        return resources
