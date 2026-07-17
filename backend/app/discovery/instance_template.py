"""Compute instance template discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.instance_template")


class InstanceTemplateDiscoverer(BaseDiscoverer):
    """Discovers compute instance templates."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.InstanceTemplatesClient(credentials=self.credentials)
            request = compute_v1.ListInstanceTemplatesRequest(project=project_id)
            for tpl in client.list(request=request):
                props = tpl.properties
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.INSTANCE_TEMPLATE,
                    name=tpl.name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_compute_instance_template",
                    terraform_resource_name=self.sanitize_name(tpl.name),
                    terraform_import_id=f"projects/{project_id}/global/instanceTemplates/{tpl.name}",
                    attributes={
                        "machine_type": props.machine_type.split("/")[-1] if props and props.machine_type else "",
                        "description": tpl.description or "",
                        "labels": dict(props.labels) if props and props.labels else {},
                    },
                ))
            logger.info(f"Discovered {len(resources)} instance templates in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering instance templates in {project_id}: {e}")
        return resources
