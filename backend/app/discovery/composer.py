"""Cloud Composer environment discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.composer")


class ComposerDiscoverer(BaseDiscoverer):
    """Discovers Cloud Composer environments."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("composer", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            response = service.projects().locations().environments().list(parent=parent).execute()

            for env in response.get("environments", []):
                name = env["name"].split("/")[-1]
                location = env["name"].split("/locations/")[1].split("/")[0]
                config = env.get("config", {})

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.COMPOSER,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_composer_environment",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=env["name"],
                    attributes={
                        "region": location,
                        "node_count": config.get("nodeConfig", {}).get("nodeCount", 3),
                        "machine_type": config.get("nodeConfig", {}).get("machineType", ""),
                        "image_version": config.get("softwareConfig", {}).get("imageVersion", ""),
                        "python_version": config.get("softwareConfig", {}).get("pythonVersion", "3"),
                        "labels": env.get("labels", {}),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} Composer envs in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Composer in {project_id}: {e}")
        return resources
