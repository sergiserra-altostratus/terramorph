"""Compute custom image discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.compute_image")


class ComputeImageDiscoverer(BaseDiscoverer):
    """Discovers custom compute images."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.ImagesClient(credentials=self.credentials)
            request = compute_v1.ListImagesRequest(project=project_id)
            for image in client.list(request=request):
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.COMPUTE_IMAGE,
                    name=image.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_image",
                    terraform_resource_name=self.sanitize_name(image.name),
                    terraform_import_id=f"projects/{project_id}/global/images/{image.name}",
                    attributes={
                        "source_disk": image.source_disk.split("/")[-1] if image.source_disk else "",
                        "family": image.family or "",
                        "disk_size_gb": image.disk_size_gb or 10,
                        "labels": dict(image.labels) if image.labels else {},
                    },
                ))
            logger.info(f"Discovered {len(resources)} images in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering images in {project_id}: {e}")
        return resources
