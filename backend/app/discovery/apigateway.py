"""API Gateway discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.apigateway")


class APIGatewayDiscoverer(BaseDiscoverer):
    """Discovers API Gateway APIs."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("apigateway", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/global"
            response = service.projects().locations().apis().list(parent=parent).execute()

            for api in response.get("apis", []):
                name = api["name"].split("/")[-1]
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.API_GATEWAY,
                    name=name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_api_gateway_api",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=api["name"],
                    attributes={
                        "api_id": name,
                        "display_name": api.get("displayName", ""),
                        "labels": api.get("labels", {}),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} API Gateways in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering API Gateway in {project_id}: {e}")
        return resources
