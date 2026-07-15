"""Secret Manager discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.secrets")


class SecretManagerDiscoverer(BaseDiscoverer):
    """Discovers Secret Manager secrets (metadata only, NOT values)."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all secrets in a project (metadata only)."""
        resources = []

        try:
            service = build("secretmanager", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}"
            request = service.projects().secrets().list(parent=parent)
            response = request.execute()

            for secret in response.get("secrets", []):
                name = secret["name"].split("/")[-1]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.SECRET,
                    name=name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_secret_manager_secret",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"projects/{project_id}/secrets/{name}",
                    attributes={
                        "secret_id": name,
                        "replication_type": "automatic"
                        if secret.get("replication", {}).get("automatic")
                        else "user_managed",
                        "labels": secret.get("labels", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} secrets in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering secrets in {project_id}: {e}")

        return resources
