"""Cloud Tasks queue discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.tasks")


class CloudTasksDiscoverer(BaseDiscoverer):
    """Discovers Cloud Tasks queues."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("cloudtasks", "v2", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            response = service.projects().locations().queues().list(parent=parent).execute()

            for queue in response.get("queues", []):
                name = queue["name"].split("/")[-1]
                location = queue["name"].split("/locations/")[1].split("/")[0]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_TASKS,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_cloud_tasks_queue",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=queue["name"],
                    attributes={
                        "location": location,
                        "rate_limits": queue.get("rateLimits", {}),
                        "retry_config": queue.get("retryConfig", {}),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} Cloud Tasks queues in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Cloud Tasks in {project_id}: {e}")
        return resources
