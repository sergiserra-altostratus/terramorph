"""Cloud Run service discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.cloudrun")


class CloudRunDiscoverer(BaseDiscoverer):
    """Discovers Cloud Run services."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Cloud Run services in a project."""
        resources = []

        try:
            service = build("run", "v2", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            request = service.projects().locations().services().list(parent=parent)
            response = request.execute()

            for svc in response.get("services", []):
                name = svc["name"].split("/")[-1]
                location = svc["name"].split("/locations/")[1].split("/")[0]

                template = svc.get("template", {})
                containers = template.get("containers", [{}])
                container = containers[0] if containers else {}

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_RUN,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_cloud_run_v2_service",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=svc["name"],
                    attributes={
                        "image": container.get("image", ""),
                        "port": container.get("ports", [{}])[0].get("containerPort", 8080)
                        if container.get("ports")
                        else 8080,
                        "cpu_limit": container.get("resources", {})
                        .get("limits", {})
                        .get("cpu", "1000m"),
                        "memory_limit": container.get("resources", {})
                        .get("limits", {})
                        .get("memory", "512Mi"),
                        "max_instance_count": template.get("scaling", {}).get(
                            "maxInstanceCount", 100
                        ),
                        "min_instance_count": template.get("scaling", {}).get(
                            "minInstanceCount", 0
                        ),
                        "ingress": svc.get("ingress", "INGRESS_TRAFFIC_ALL"),
                        "labels": svc.get("labels", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} Cloud Run services in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Cloud Run in {project_id}: {e}")

        return resources
