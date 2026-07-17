"""Compute Reservation discovery."""

import uuid
from google.cloud import compute_v1
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.reservation")


class ComputeReservationDiscoverer(BaseDiscoverer):
    """Discovers Compute Reservations."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            client = compute_v1.ReservationsClient(credentials=self.credentials)
            request = compute_v1.AggregatedListReservationsRequest(project=project_id)
            for zone, response in client.aggregated_list(request=request):
                if response.reservations:
                    for res in response.reservations:
                        zone_name = zone.split("/")[-1]
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.COMPUTE_RESERVATION,
                            name=res.name,
                            project=project_id,
                            location=zone_name,
                            terraform_resource_type="google_compute_reservation",
                            terraform_resource_name=self.sanitize_name(res.name),
                            terraform_import_id=f"projects/{project_id}/zones/{zone_name}/reservations/{res.name}",
                            attributes={"zone": zone_name, "description": res.description or ""},
                        ))
            logger.info(f"Discovered {len(resources)} reservations in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering reservations in {project_id}: {e}")
        return resources
