"""AWS Secrets Manager discovery (metadata only, NOT values)."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.secrets")


class SecretsManagerDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("secretsmanager")
            paginator = client.get_paginator("list_secrets")
            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    name = secret["Name"]
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_SECRETS_MANAGER, name=name,
                        project=self.region, location=self.region,
                        terraform_resource_type="aws_secretsmanager_secret",
                        terraform_resource_name=self.sanitize_name(name),
                        terraform_import_id=secret.get("ARN", name),
                        attributes={
                            "name": name,
                            "arn": secret.get("ARN", ""),
                            "description": secret.get("Description", ""),
                            "kms_key_id": secret.get("KmsKeyId", ""),
                        },
                    ))
            logger.info(f"Discovered {len(resources)} secrets")
        except Exception as e:
            logger.error(f"Error discovering Secrets Manager: {e}")
        return resources
