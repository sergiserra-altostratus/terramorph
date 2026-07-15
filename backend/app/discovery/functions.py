"""Cloud Functions discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.functions")


class CloudFunctionsDiscoverer(BaseDiscoverer):
    """Discovers Cloud Functions (Gen 1 & Gen 2)."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Cloud Functions in a project."""
        resources = []

        try:
            service = build("cloudfunctions", "v2", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            request = service.projects().locations().functions().list(parent=parent)
            response = request.execute()

            for function in response.get("functions", []):
                name = function["name"].split("/")[-1]
                location = function["name"].split("/locations/")[1].split("/")[0]

                build_config = function.get("buildConfig", {})
                service_config = function.get("serviceConfig", {})

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_FUNCTION,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_cloudfunctions2_function",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=function["name"],
                    attributes={
                        "runtime": build_config.get("runtime", ""),
                        "entry_point": build_config.get("entryPoint", ""),
                        "source": build_config.get("source", {}),
                        "available_memory": service_config.get("availableMemory", "256M"),
                        "timeout_seconds": service_config.get("timeoutSeconds", 60),
                        "max_instance_count": service_config.get("maxInstanceCount", 100),
                        "min_instance_count": service_config.get("minInstanceCount", 0),
                        "environment": function.get("environment", "GEN_2"),
                        "labels": function.get("labels", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} Cloud Functions in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Cloud Functions in {project_id}: {e}")

        return resources
