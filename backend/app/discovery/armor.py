"""Cloud Armor security policy discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.armor")


class CloudArmorDiscoverer(BaseDiscoverer):
    """Discovers Cloud Armor security policies."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.SecurityPoliciesClient(credentials=self.credentials)
            request = compute_v1.ListSecurityPoliciesRequest(project=project_id)

            for policy in client.list(request=request):
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_ARMOR,
                    name=policy.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_security_policy",
                    terraform_resource_name=self.sanitize_name(policy.name),
                    terraform_import_id=f"projects/{project_id}/global/securityPolicies/{policy.name}",
                    attributes={
                        "description": policy.description or "",
                        "type": policy.type_ if hasattr(policy, 'type_') else "CLOUD_ARMOR",
                        "rules_count": len(policy.rules) if policy.rules else 0,
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} Cloud Armor policies in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Cloud Armor in {project_id}: {e}")
        return resources
