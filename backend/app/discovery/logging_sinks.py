"""Cloud Logging sinks discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.logging")


class LoggingSinksDiscoverer(BaseDiscoverer):
    """Discovers Cloud Logging sinks (log exports)."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("logging", "v2", credentials=self.credentials)
            parent = f"projects/{project_id}"
            response = service.projects().sinks().list(parent=parent).execute()

            for sink in response.get("sinks", []):
                name = sink.get("name", "")
                # Skip default sinks
                if name.startswith("_"):
                    continue

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.LOGGING_SINK,
                    name=name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_logging_project_sink",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"projects/{project_id}/sinks/{name}",
                    attributes={
                        "destination": sink.get("destination", ""),
                        "filter": sink.get("filter", ""),
                        "unique_writer_identity": sink.get("writerIdentity", ""),
                        "disabled": sink.get("disabled", False),
                        "description": sink.get("description", ""),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} logging sinks in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering logging sinks in {project_id}: {e}")
        return resources
