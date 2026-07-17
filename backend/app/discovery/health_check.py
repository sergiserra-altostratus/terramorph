"""Compute Health Check discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.health_check")


class HealthCheckDiscoverer(BaseDiscoverer):
    """Discovers Compute Health Checks."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.HealthChecksClient(credentials=self.credentials)
            request = compute_v1.ListHealthChecksRequest(project=project_id)
            for hc in client.list(request=request):
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.HEALTH_CHECK,
                    name=hc.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_health_check",
                    terraform_resource_name=self.sanitize_name(hc.name),
                    terraform_import_id=f"projects/{project_id}/global/healthChecks/{hc.name}",
                    attributes={
                        "check_interval_sec": hc.check_interval_sec or 5,
                        "timeout_sec": hc.timeout_sec or 5,
                        "healthy_threshold": hc.healthy_threshold or 2,
                        "unhealthy_threshold": hc.unhealthy_threshold or 2,
                        "description": hc.description or "",
                    },
                ))
            logger.info(f"Discovered {len(resources)} health checks in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering health checks in {project_id}: {e}")
        return resources
