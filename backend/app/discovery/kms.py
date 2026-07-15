"""Cloud KMS KeyRing and CryptoKey discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.kms")


class CloudKMSDiscoverer(BaseDiscoverer):
    """Discovers Cloud KMS KeyRings."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all KMS key rings in a project."""
        resources = []

        try:
            service = build("cloudkms", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            request = service.projects().locations().keyRings().list(parent=parent)
            response = request.execute()

            for keyring in response.get("keyRings", []):
                name = keyring["name"].split("/")[-1]
                location = keyring["name"].split("/locations/")[1].split("/")[0]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.KMS_KEYRING,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_kms_key_ring",
                    terraform_resource_name=self.sanitize_name(f"{location}_{name}"),
                    terraform_import_id=keyring["name"],
                    attributes={
                        "location": location,
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} KMS keyrings in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering KMS in {project_id}: {e}")

        return resources
