"""Bigtable instance discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.bigtable")


class BigtableDiscoverer(BaseDiscoverer):
    """Discovers Bigtable instances."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("bigtableadmin", "v2", credentials=self.credentials)
            parent = f"projects/{project_id}"
            response = service.projects().instances().list(parent=parent).execute()
            for inst in response.get("instances", []):
                name = inst["name"].split("/")[-1]
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.BIGTABLE_INSTANCE,
                    name=name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_bigtable_instance",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"projects/{project_id}/instances/{name}",
                    attributes={
                        "display_name": inst.get("displayName", ""),
                        "instance_type": inst.get("type", "PRODUCTION"),
                        "labels": inst.get("labels", {}),
                    },
                ))
            logger.info(f"Discovered {len(resources)} Bigtable instances in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Bigtable in {project_id}: {e}")
        return resources
