"""Filestore instance discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.filestore")


class FilestoreDiscoverer(BaseDiscoverer):
    """Discovers Filestore instances."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("file", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            response = service.projects().locations().instances().list(parent=parent).execute()

            for inst in response.get("instances", []):
                name = inst["name"].split("/")[-1]
                location = inst["name"].split("/locations/")[1].split("/")[0]
                file_shares = inst.get("fileShares", [{}])
                share = file_shares[0] if file_shares else {}

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.FILESTORE,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_filestore_instance",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=inst["name"],
                    attributes={
                        "tier": inst.get("tier", "BASIC_HDD"),
                        "zone": location,
                        "file_share_name": share.get("name", "share1"),
                        "capacity_gb": int(share.get("capacityGb", 1024)),
                        "network": inst.get("networks", [{}])[0].get("network", "default"),
                        "labels": inst.get("labels", {}),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} Filestore instances in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Filestore in {project_id}: {e}")
        return resources
