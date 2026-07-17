"""Vertex AI Endpoint discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.vertex_ai")


class VertexAIDiscoverer(BaseDiscoverer):
    """Discovers Vertex AI Endpoints."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("aiplatform", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            response = service.projects().locations().endpoints().list(parent=parent).execute()
            for ep in response.get("endpoints", []):
                name = ep["name"].split("/")[-1]
                location = ep["name"].split("/locations/")[1].split("/")[0]
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.VERTEX_AI_ENDPOINT,
                    name=ep.get("displayName", name),
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_vertex_ai_endpoint",
                    terraform_resource_name=self.sanitize_name(ep.get("displayName", name)),
                    terraform_import_id=ep["name"],
                    attributes={
                        "display_name": ep.get("displayName", ""),
                        "description": ep.get("description", ""),
                        "region": location,
                        "labels": ep.get("labels", {}),
                    },
                ))
            logger.info(f"Discovered {len(resources)} Vertex AI endpoints in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Vertex AI in {project_id}: {e}")
        return resources
