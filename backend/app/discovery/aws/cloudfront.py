"""AWS CloudFront distribution discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.cloudfront")


class CloudFrontDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            cf = self.session.client("cloudfront")
            distributions = cf.list_distributions().get("DistributionList", {}).get("Items", [])
            for dist in distributions:
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_CLOUDFRONT, name=dist.get("Comment", dist["Id"]),
                    project="global", location="global",
                    terraform_resource_type="aws_cloudfront_distribution",
                    terraform_resource_name=self.sanitize_name(dist["Id"]),
                    terraform_import_id=dist["Id"],
                    attributes={"distribution_id": dist["Id"], "domain_name": dist.get("DomainName", ""), "status": dist.get("Status", ""), "enabled": dist.get("Enabled", True), "comment": dist.get("Comment", "")},
                ))
            logger.info(f"Discovered {len(resources)} CloudFront distributions")
        except Exception as e:
            logger.error(f"Error discovering CloudFront: {e}")
        return resources
