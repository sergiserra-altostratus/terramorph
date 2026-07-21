"""AWS S3 bucket discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.s3")


class S3Discoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            s3 = self.session.client("s3")
            for bucket in s3.list_buckets().get("Buckets", []):
                name = bucket["Name"]
                try:
                    loc = s3.get_bucket_location(Bucket=name)
                    region = loc.get("LocationConstraint") or "us-east-1"
                except Exception:
                    region = "unknown"
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_S3_BUCKET, name=name,
                    project=self.region, location=region,
                    terraform_resource_type="aws_s3_bucket",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=name,
                    attributes={"bucket": name, "region": region},
                ))
            logger.info(f"Discovered {len(resources)} S3 buckets")
        except Exception as e:
            logger.error(f"Error discovering S3: {e}")
        return resources
