"""Custom IAM Roles discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.custom_roles")


class CustomRolesDiscoverer(BaseDiscoverer):
    """Discovers custom IAM roles at project level."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all custom roles in a project."""
        resources = []

        try:
            service = build("iam", "v1", credentials=self.credentials)
            request = service.projects().roles().list(
                parent=f"projects/{project_id}",
                showDeleted=False,
            )
            response = request.execute()

            for role in response.get("roles", []):
                name = role["name"].split("/")[-1]
                role_id = role.get("name", "").split("/roles/")[-1]

                # Get full role details with permissions
                detail_request = service.projects().roles().get(name=role["name"])
                detail = detail_request.execute()

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.CUSTOM_ROLE,
                    name=name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_project_iam_custom_role",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=f"projects/{project_id}/roles/{role_id}",
                    attributes={
                        "role_id": role_id,
                        "title": detail.get("title", ""),
                        "description": detail.get("description", ""),
                        "permissions": detail.get("includedPermissions", []),
                        "stage": detail.get("stage", "GA"),
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} custom roles in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering custom roles in {project_id}: {e}")

        return resources
