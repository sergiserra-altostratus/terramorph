"""Compute SSL Policy discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.ssl_policy")


class SSLPolicyDiscoverer(BaseDiscoverer):
    """Discovers Compute SSL Policies."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.SslPoliciesClient(credentials=self.credentials)
            request = compute_v1.ListSslPoliciesRequest(project=project_id)
            for policy in client.list(request=request):
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.SSL_POLICY,
                    name=policy.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_ssl_policy",
                    terraform_resource_name=self.sanitize_name(policy.name),
                    terraform_import_id=f"projects/{project_id}/global/sslPolicies/{policy.name}",
                    attributes={
                        "min_tls_version": policy.min_tls_version or "TLS_1_2",
                        "profile": policy.profile or "MODERN",
                        "description": policy.description or "",
                    },
                ))
            logger.info(f"Discovered {len(resources)} SSL policies in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering SSL policies in {project_id}: {e}")
        return resources
