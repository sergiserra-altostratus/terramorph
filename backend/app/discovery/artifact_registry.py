"""Artifact Registry repository discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.artifact_registry")


class ArtifactRegistryDiscoverer(BaseDiscoverer):
    """Discovers Artifact Registry repositories."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Artifact Registry repositories in a project."""
        resources = []

        try:
            service = build("artifactregistry", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            request = service.projects().locations().repositories().list(parent=parent)
            response = request.execute()

            for repo in response.get("repositories", []):
                name = repo["name"].split("/")[-1]
                location = repo["name"].split("/locations/")[1].split("/")[0]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.ARTIFACT_REGISTRY,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_artifact_registry_repository",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=repo["name"],
                    attributes={
                        "repository_id": name,
                        "location": location,
                        "format": repo.get("format", "DOCKER"),
                        "description": repo.get("description", ""),
                        "mode": repo.get("mode", "STANDARD_REPOSITORY"),
                        "labels": repo.get("labels", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} AR repos in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Artifact Registry in {project_id}: {e}")

        return resources
