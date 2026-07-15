"""Google Cloud Storage bucket discovery."""

import uuid

from google.cloud import storage

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.storage")


class StorageDiscoverer(BaseDiscoverer):
    """Discovers GCS Buckets."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all GCS buckets in a project."""
        resources = []

        try:
            client = storage.Client(project=project_id, credentials=self.credentials)

            for bucket in client.list_buckets():
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.GCS_BUCKET,
                    name=bucket.name,
                    project=project_id,
                    location=bucket.location or "US",
                    terraform_resource_type="google_storage_bucket",
                    terraform_resource_name=self.sanitize_name(bucket.name),
                    terraform_import_id=bucket.name,
                    attributes={
                        "location": bucket.location or "US",
                        "storage_class": bucket.storage_class or "STANDARD",
                        "versioning_enabled": bucket.versioning_enabled or False,
                        "uniform_bucket_level_access": (
                            bucket.iam_configuration.uniform_bucket_level_access_enabled
                            if bucket.iam_configuration
                            else False
                        ),
                        "labels": dict(bucket.labels) if bucket.labels else {},
                        "lifecycle_rules": [
                            {
                                "action": rule.get("action", {}),
                                "condition": rule.get("condition", {}),
                            }
                            for rule in (bucket.lifecycle_rules or [])
                        ],
                        "force_destroy": False,
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} GCS buckets in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering GCS buckets in {project_id}: {e}")

        return resources
