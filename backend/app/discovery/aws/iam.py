"""AWS IAM roles and policies discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.iam")


class IAMDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            iam = self.session.client("iam")

            # Roles
            paginator = iam.get_paginator("list_roles")
            for page in paginator.paginate():
                for role in page["Roles"]:
                    # Skip AWS service-linked roles
                    if role["Path"].startswith("/aws-service-role/"):
                        continue
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_IAM_ROLE, name=role["RoleName"],
                        project="global", location="global",
                        terraform_resource_type="aws_iam_role",
                        terraform_resource_name=self.sanitize_name(role["RoleName"]),
                        terraform_import_id=role["RoleName"],
                        attributes={"role_name": role["RoleName"], "arn": role["Arn"], "path": role["Path"], "description": role.get("Description", "")},
                    ))

            logger.info(f"Discovered {len(resources)} IAM resources")
        except Exception as e:
            logger.error(f"Error discovering IAM: {e}")
        return resources
