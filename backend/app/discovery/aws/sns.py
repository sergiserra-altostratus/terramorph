"""AWS SNS topic discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.sns")


class SNSDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("sns")
            paginator = client.get_paginator("list_topics")
            for page in paginator.paginate():
                for topic in page.get("Topics", []):
                    arn = topic["TopicArn"]
                    name = arn.split(":")[-1]
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_SNS_TOPIC, name=name,
                        project=self.region, location=self.region,
                        terraform_resource_type="aws_sns_topic",
                        terraform_resource_name=self.sanitize_name(name),
                        terraform_import_id=arn,
                        attributes={"name": name, "arn": arn},
                    ))
            logger.info(f"Discovered {len(resources)} SNS topics")
        except Exception as e:
            logger.error(f"Error discovering SNS: {e}")
        return resources
