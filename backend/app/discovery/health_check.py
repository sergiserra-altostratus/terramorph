"""Compute Health Check discovery (global + regional)."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.health_check")


class HealthCheckDiscoverer(BaseDiscoverer):
    """Discovers Compute Health Checks (global and regional)."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []

        # Global health checks
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
                        "scope": "global",
                    },
                ))
        except Exception as e:
            logger.error(f"Error discovering global health checks in {project_id}: {e}")

        # Regional health checks
        try:
            regional_client = compute_v1.RegionHealthChecksClient(credentials=self.credentials)
            request = compute_v1.AggregatedListHealthChecksRequest(project=project_id)
            agg_client = compute_v1.HealthChecksClient(credentials=self.credentials)

            for scope_key, scoped_list in agg_client.aggregated_list(request=request):
                if scoped_list.health_checks:
                    region_name = scope_key.split("/")[-1]
                    for hc in scoped_list.health_checks:
                        if "regions/" not in (hc.self_link or ""):
                            continue
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.HEALTH_CHECK,
                            name=hc.name,
                            project=project_id,
                            location=region_name,
                            terraform_resource_type="google_compute_region_health_check",
                            terraform_resource_name=self.sanitize_name(f"{region_name}_{hc.name}"),
                            terraform_import_id=f"projects/{project_id}/regions/{region_name}/healthChecks/{hc.name}",
                            attributes={
                                "check_interval_sec": hc.check_interval_sec or 5,
                                "timeout_sec": hc.timeout_sec or 5,
                                "healthy_threshold": hc.healthy_threshold or 2,
                                "unhealthy_threshold": hc.unhealthy_threshold or 2,
                                "description": hc.description or "",
                                "scope": "regional",
                                "region": region_name,
                            },
                        ))
        except Exception as e:
            logger.error(f"Error discovering regional health checks in {project_id}: {e}")

        logger.info(f"Discovered {len(resources)} health checks (global+regional) in {project_id}")
        return resources
