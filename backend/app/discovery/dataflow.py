"""Dataflow job discovery (templates/flex templates)."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.dataflow")


class DataflowDiscoverer(BaseDiscoverer):
    """Discovers active Dataflow jobs."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("dataflow", "v1b3", credentials=self.credentials)
            response = service.projects().jobs().list(
                projectId=project_id, filter="ACTIVE"
            ).execute()

            for job in response.get("jobs", []):
                name = job.get("name", "unknown")
                location = job.get("location", "us-central1")

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.DATAFLOW_JOB,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_dataflow_job",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"projects/{project_id}/locations/{location}/jobs/{job['id']}",
                    attributes={
                        "template_gcs_path": job.get("jobMetadata", {}).get("sdkVersion", {}).get("sdkSupportStatus", ""),
                        "temp_gcs_location": "",
                        "region": location,
                        "type": job.get("type", ""),
                        "state": job.get("currentState", ""),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} Dataflow jobs in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering Dataflow in {project_id}: {e}")
        return resources
