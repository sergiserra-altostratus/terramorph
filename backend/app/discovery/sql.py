"""Cloud SQL instance discovery."""

import uuid

from googleapiclient.discovery import build
from google.auth.credentials import Credentials

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.sql")


class CloudSQLDiscoverer(BaseDiscoverer):
    """Discovers Cloud SQL instances."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all Cloud SQL instances in a project."""
        resources = []

        try:
            service = build("sqladmin", "v1beta4", credentials=self.credentials)
            request = service.instances().list(project=project_id)
            response = request.execute()

            for instance in response.get("items", []):
                settings = instance.get("settings", {})
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CLOUD_SQL,
                    name=instance["name"],
                    project=project_id,
                    location=instance.get("region", ""),
                    terraform_resource_type="google_sql_database_instance",
                    terraform_resource_name=self.sanitize_name(instance["name"]),
                    terraform_import_id=f"projects/{project_id}/instances/{instance['name']}",
                    attributes={
                        "database_version": instance.get("databaseVersion", ""),
                        "region": instance.get("region", ""),
                        "tier": settings.get("tier", ""),
                        "availability_type": settings.get("availabilityType", ""),
                        "disk_size": settings.get("dataDiskSizeGb", 10),
                        "disk_type": settings.get("dataDiskType", "PD_SSD"),
                        "backup_enabled": settings.get("backupConfiguration", {}).get(
                            "enabled", False
                        ),
                        "ipv4_enabled": settings.get("ipConfiguration", {}).get(
                            "ipv4Enabled", True
                        ),
                        "labels": settings.get("userLabels", {}),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} Cloud SQL instances in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering Cloud SQL in {project_id}: {e}")

        return resources
