"""DNS Policy discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.dns_policy")


class DNSPolicyDiscoverer(BaseDiscoverer):
    """Discovers Cloud DNS policies."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("dns", "v1", credentials=self.credentials)
            response = service.policies().list(project=project_id).execute()
            for policy in response.get("policies", []):
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.DNS_POLICY,
                    name=policy["name"],
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_dns_policy",
                    terraform_resource_name=self.sanitize_name(policy["name"]),
                    terraform_import_id=f"projects/{project_id}/policies/{policy['name']}",
                    attributes={
                        "enable_inbound_forwarding": policy.get("enableInboundForwarding", False),
                        "enable_logging": policy.get("enableLogging", False),
                        "description": policy.get("description", ""),
                        "networks": [n.get("networkUrl", "").split("/")[-1] for n in policy.get("networks", [])],
                    },
                ))
            logger.info(f"Discovered {len(resources)} DNS policies in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering DNS policies in {project_id}: {e}")
        return resources
