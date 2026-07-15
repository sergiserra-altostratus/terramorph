"""Cloud Spanner instance discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.spanner")


class SpannerDiscoverer(BaseDiscoverer):
    """Discovers Cloud Spanner instances."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("spanner", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}"
            response = service.projects().instances().list(parent=parent).execute()

            for inst in response.get("instances", []):
                name = inst["name"].split("/")[-1]
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.SPANNER_INSTANCE,
                    name=name,
                    project=project_id,
                    location=inst.get("config", "").split("/")[-1],
                    terraform_resource_type="google_spanner_instance",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"{project_id}/{name}",
                    attributes={
                        "config": inst.get("config", "").split("/")[-1],
                        "display_name": inst.get("displayName", ""),
                        "num_nodes": inst.get("nodeCount", 1),
                        "processing_units": inst.get("processingUnits", 0),
                        "labels": inst.get("labels", {}),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} Spanner instances in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Spanner in {project_id}: {e}")
        return resources
