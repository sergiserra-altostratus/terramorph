"""Cloud Scheduler job discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.scheduler")


class CloudSchedulerDiscoverer(BaseDiscoverer):
    """Discovers Cloud Scheduler jobs."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Cloud Scheduler jobs in a project."""
        resources = []

        try:
            service = build("cloudscheduler", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            request = service.projects().locations().jobs().list(parent=parent)
            response = request.execute()

            for job in response.get("jobs", []):
                name = job["name"].split("/")[-1]
                location = job["name"].split("/locations/")[1].split("/")[0]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_SCHEDULER,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_cloud_scheduler_job",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=job["name"],
                    attributes={
                        "schedule": job.get("schedule", ""),
                        "time_zone": job.get("timeZone", "UTC"),
                        "description": job.get("description", ""),
                        "http_target": job.get("httpTarget", {}),
                        "pubsub_target": job.get("pubsubTarget", {}),
                        "attempt_deadline": job.get("attemptDeadline", ""),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} scheduler jobs in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Cloud Scheduler in {project_id}: {e}")

        return resources
