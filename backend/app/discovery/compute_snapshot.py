"""Compute snapshot discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.snapshot")


class ComputeSnapshotDiscoverer(BaseDiscoverer):
    """Discovers compute disk snapshots."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.SnapshotsClient(credentials=self.credentials)
            request = compute_v1.ListSnapshotsRequest(project=project_id)
            for snap in client.list(request=request):
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.COMPUTE_SNAPSHOT,
                    name=snap.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_snapshot",
                    terraform_resource_name=self.sanitize_name(snap.name),
                    terraform_import_id=f"projects/{project_id}/global/snapshots/{snap.name}",
                    attributes={
                        "source_disk": snap.source_disk.split("/")[-1] if snap.source_disk else "",
                        "storage_bytes": snap.storage_bytes or 0,
                        "labels": dict(snap.labels) if snap.labels else {},
                    },
                ))
            logger.info(f"Discovered {len(resources)} snapshots in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering snapshots in {project_id}: {e}")
        return resources
