"""IAM Policy Bindings discovery."""

import uuid

from googleapiclient.discovery import build

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.iam_bindings")


class IAMBindingsDiscoverer(BaseDiscoverer):
    """Discovers project-level IAM policy bindings."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all IAM policy bindings for a project."""
        resources = []

        try:
            service = build("cloudresourcemanager", "v1", credentials=self.credentials)
            request = service.projects().getIamPolicy(
                resource=project_id,
                body={"options": {"requestedPolicyVersion": 3}},
            )
            policy = request.execute()

            for binding in policy.get("bindings", []):
                role = binding.get("role", "")
                members = binding.get("members", [])
                condition = binding.get("condition")

                # Create a sanitized name from the role
                role_short = role.split("/")[-1].replace(".", "_").replace("-", "_")
                binding_name = f"{role_short}"

                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.IAM_BINDING,
                    name=binding_name,
                    project=project_id,
                    location="global",
                    terraform_resource_type="google_project_iam_binding",
                    terraform_resource_name=self.sanitize_name(binding_name),
                    terraform_import_id=f"{project_id} {role}",
                    attributes={
                        "project": project_id,
                        "role": role,
                        "members": members,
                        "condition": {
                            "title": condition.get("title", ""),
                            "description": condition.get("description", ""),
                            "expression": condition.get("expression", ""),
                        }
                        if condition
                        else None,
                    },
                )
                resources.append(resource)

            logger.info(
                f"Discovered {len(resources)} IAM bindings in {project_id}"
            )

        except Exception as e:
            logger.error(f"Error discovering IAM bindings in {project_id}: {e}")

        return resources
