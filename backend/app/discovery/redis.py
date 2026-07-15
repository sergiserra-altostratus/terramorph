"""Memorystore (Redis) instance discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.redis")


class MemorystoreDiscoverer(BaseDiscoverer):
    """Discovers Memorystore Redis instances."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Redis instances in a project."""
        resources = []

        try:
            service = build("redis", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            request = service.projects().locations().instances().list(parent=parent)
            response = request.execute()

            for instance in response.get("instances", []):
                name = instance["name"].split("/")[-1]
                location = instance["name"].split("/locations/")[1].split("/")[0]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.MEMORYSTORE_REDIS,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_redis_instance",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=instance["name"],
                    attributes={
                        "tier": instance.get("tier", "BASIC"),
                        "memory_size_gb": instance.get("memorySizeGb", 1),
                        "redis_version": instance.get("redisVersion", ""),
                        "region": location,
                        "authorized_network": instance.get("authorizedNetwork", ""),
                        "connect_mode": instance.get("connectMode", "DIRECT_PEERING"),
                        "display_name": instance.get("displayName", ""),
                        "labels": instance.get("labels", {}),
                        "redis_configs": instance.get("redisConfigs", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} Redis instances in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Redis instances in {project_id}: {e}")

        return resources
