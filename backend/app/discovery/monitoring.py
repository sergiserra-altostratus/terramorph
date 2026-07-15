"""Cloud Monitoring alert policy discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.monitoring")


class MonitoringAlertsDiscoverer(BaseDiscoverer):
    """Discovers Cloud Monitoring alert policies."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("monitoring", "v3", credentials=self.credentials)
            name = f"projects/{project_id}"
            response = service.projects().alertPolicies().list(name=name).execute()

            for policy in response.get("alertPolicies", []):
                display_name = policy.get("displayName", "unnamed")
                policy_name = policy["name"].split("/")[-1]

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.MONITORING_ALERT,
                    name=display_name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_monitoring_alert_policy",
                    terraform_resource_name=self.sanitize_name(display_name),
                    terraform_import_id=policy["name"],
                    attributes={
                        "display_name": display_name,
                        "combiner": policy.get("combiner", "OR"),
                        "enabled": policy.get("enabled", True),
                        "conditions_count": len(policy.get("conditions", [])),
                        "notification_channels": policy.get("notificationChannels", []),
                    },
                )
                resources.append(resource)
            logger.info(f"Discovered {len(resources)} alert policies in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering monitoring alerts in {project_id}: {e}")
        return resources
