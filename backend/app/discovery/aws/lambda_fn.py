"""AWS Lambda function discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.lambda")


class LambdaDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            lam = self.session.client("lambda")
            paginator = lam.get_paginator("list_functions")
            for page in paginator.paginate():
                for fn in page["Functions"]:
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_LAMBDA, name=fn["FunctionName"],
                        project=self.region, location=self.region,
                        terraform_resource_type="aws_lambda_function",
                        terraform_resource_name=self.sanitize_name(fn["FunctionName"]),
                        terraform_import_id=fn["FunctionName"],
                        attributes={"function_name": fn["FunctionName"], "runtime": fn.get("Runtime", ""), "handler": fn.get("Handler", ""), "memory_size": fn.get("MemorySize", 128), "timeout": fn.get("Timeout", 3), "role": fn.get("Role", ""), "description": fn.get("Description", "")},
                    ))
            logger.info(f"Discovered {len(resources)} Lambda functions")
        except Exception as e:
            logger.error(f"Error discovering Lambda: {e}")
        return resources
