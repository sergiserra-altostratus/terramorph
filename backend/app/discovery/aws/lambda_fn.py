"""AWS Lambda function discovery with comprehensive attributes."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.lambda")


class LambdaDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("lambda")
            paginator = client.get_paginator("list_functions")
            for page in paginator.paginate():
                for fn in page["Functions"]:
                    name = fn["FunctionName"]

                    # Environment variables
                    environment = fn.get("Environment", {}).get("Variables", {})

                    # VPC config
                    vpc_config = None
                    vpc = fn.get("VpcConfig", {})
                    if vpc.get("SubnetIds"):
                        vpc_config = {
                            "subnet_ids": vpc.get("SubnetIds", []),
                            "security_group_ids": vpc.get("SecurityGroupIds", []),
                        }

                    # Tracing config
                    tracing_config = None
                    tracing = fn.get("TracingConfig", {})
                    if tracing.get("Mode") and tracing["Mode"] != "PassThrough":
                        tracing_config = {"mode": tracing["Mode"]}

                    # Get tags
                    tags = {}
                    try:
                        tag_resp = client.list_tags(Resource=fn["FunctionArn"])
                        tags = tag_resp.get("Tags", {})
                    except Exception:
                        pass

                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()),
                        type=ResourceType.AWS_LAMBDA,
                        name=name,
                        project=self.region,
                        location=self.region,
                        terraform_resource_type="aws_lambda_function",
                        terraform_resource_name=self.sanitize_name(name),
                        terraform_import_id=name,
                        attributes={
                            "function_name": name,
                            "role": fn.get("Role", ""),
                            "handler": fn.get("Handler", ""),
                            "runtime": fn.get("Runtime", ""),
                            "description": fn.get("Description", ""),
                            "memory_size": fn.get("MemorySize", 128),
                            "timeout": fn.get("Timeout", 3),
                            "architectures": fn.get("Architectures", ["x86_64"]),
                            "layers": [l["Arn"] for l in fn.get("Layers", [])],
                            "environment": environment if environment else None,
                            "vpc_config": vpc_config,
                            "tracing_config": tracing_config,
                            "tags": tags,
                        },
                    ))
            logger.info(f"Discovered {len(resources)} Lambda functions")
        except Exception as e:
            logger.error(f"Error discovering Lambda: {e}")
        return resources
