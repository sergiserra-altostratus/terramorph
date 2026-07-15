"""BigQuery dataset and table discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.bigquery")


class BigQueryDiscoverer(BaseDiscoverer):
    """Discovers BigQuery datasets."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all BigQuery datasets in a project."""
        resources = []

        try:
            service = build("bigquery", "v2", credentials=self.credentials)
            request = service.datasets().list(projectId=project_id)
            response = request.execute()

            for ds in response.get("datasets", []):
                dataset_id = ds["datasetReference"]["datasetId"]

                # Get dataset details
                detail = service.datasets().get(
                    projectId=project_id, datasetId=dataset_id
                ).execute()

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.BIGQUERY_DATASET,
                    name=dataset_id,
                    project=project_id,
                    location=detail.get("location", "US"),
                    terraform_resource_type="google_bigquery_dataset",
                    terraform_resource_name=self.sanitize_name(dataset_id),
                    terraform_import_id=f"projects/{project_id}/datasets/{dataset_id}",
                    attributes={
                        "dataset_id": dataset_id,
                        "location": detail.get("location", "US"),
                        "description": detail.get("description", ""),
                        "default_table_expiration_ms": detail.get(
                            "defaultTableExpirationMs"
                        ),
                        "default_partition_expiration_ms": detail.get(
                            "defaultPartitionExpirationMs"
                        ),
                        "labels": detail.get("labels", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} BigQuery datasets in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering BigQuery in {project_id}: {e}")

        return resources
