"""AWS SQS queue discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.sqs")


class SQSDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("sqs")
            queues = client.list_queues().get("QueueUrls", [])
            for url in queues:
                name = url.split("/")[-1]
                attrs = client.get_queue_attributes(QueueUrl=url, AttributeNames=["All"]).get("Attributes", {})
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_SQS_QUEUE, name=name,
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_sqs_queue",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=url,
                    attributes={
                        "name": name,
                        "url": url,
                        "delay_seconds": int(attrs.get("DelaySeconds", 0)),
                        "max_message_size": int(attrs.get("MaximumMessageSize", 262144)),
                        "visibility_timeout": int(attrs.get("VisibilityTimeout", 30)),
                        "fifo_queue": name.endswith(".fifo"),
                    },
                ))
            logger.info(f"Discovered {len(resources)} SQS queues")
        except Exception as e:
            logger.error(f"Error discovering SQS: {e}")
        return resources
