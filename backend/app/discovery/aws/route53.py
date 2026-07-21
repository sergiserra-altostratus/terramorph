"""AWS Route53 hosted zone discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.route53")


class Route53Discoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            r53 = self.session.client("route53")
            zones = r53.list_hosted_zones().get("HostedZones", [])
            for zone in zones:
                zone_id = zone["Id"].split("/")[-1]
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_ROUTE53_ZONE, name=zone["Name"].rstrip("."),
                    project="global", location="global",
                    terraform_resource_type="aws_route53_zone",
                    terraform_resource_name=self.sanitize_name(zone["Name"].rstrip(".")),
                    terraform_import_id=zone_id,
                    attributes={"zone_id": zone_id, "name": zone["Name"], "private_zone": zone.get("Config", {}).get("PrivateZone", False), "record_count": zone.get("ResourceRecordSetCount", 0)},
                ))
            logger.info(f"Discovered {len(resources)} Route53 zones")
        except Exception as e:
            logger.error(f"Error discovering Route53: {e}")
        return resources
