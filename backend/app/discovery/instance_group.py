"""Compute instance group (managed) discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.instance_group")


class InstanceGroupDiscoverer(BaseDiscoverer):
    """Discovers managed instance groups."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.InstanceGroupManagersClient(credentials=self.credentials)
            request = compute_v1.AggregatedListInstanceGroupManagersRequest(project=project_id)
            for zone, response in client.aggregated_list(request=request):
                if response.instance_group_managers:
                    for igm in response.instance_group_managers:
                        zone_name = zone.split("/")[-1]
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.INSTANCE_GROUP,
                            name=igm.name,
                            project=project_id,
                            location=zone_name,
                            terraform_resource_type="google_compute_instance_group_manager",
                            terraform_resource_name=self.sanitize_name(igm.name),
                            terraform_import_id=f"projects/{project_id}/zones/{zone_name}/instanceGroupManagers/{igm.name}",
                            attributes={
                                "zone": zone_name,
                                "target_size": igm.target_size or 0,
                                "base_instance_name": igm.base_instance_name or "",
                                "instance_template": igm.instance_template.split("/")[-1] if igm.instance_template else "",
                            },
                        ))
            logger.info(f"Discovered {len(resources)} instance groups in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering instance groups in {project_id}: {e}")
        return resources
