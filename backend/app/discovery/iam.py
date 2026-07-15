"""IAM Service Account discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.iam")


class IAMServiceAccountDiscoverer(BaseDiscoverer):
    """Discovers IAM Service Accounts."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all service accounts in a project."""
        resources = []

        try:
            service = build("iam", "v1", credentials=self.credentials)
            request = service.projects().serviceAccounts().list(
                name=f"projects/{project_id}"
            )
            response = request.execute()

            for sa in response.get("accounts", []):
                email = sa.get("email", "")
                # Skip default service accounts
                if email.endswith(".iam.gserviceaccount.com"):
                    account_id = email.split("@")[0]
                else:
                    continue

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.SERVICE_ACCOUNT,
                    name=account_id,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_service_account",
                    terraform_resource_name=self.sanitize_name(account_id),
                    terraform_import_id=f"projects/{project_id}/serviceAccounts/{email}",
                    attributes={
                        "account_id": account_id,
                        "display_name": sa.get("displayName", ""),
                        "description": sa.get("description", ""),
                        "disabled": sa.get("disabled", False),
                        "email": email,
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} service accounts in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering service accounts in {project_id}: {e}")

        return resources
