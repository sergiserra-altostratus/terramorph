"""AWS ELB/ALB load balancer discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.elb")


class ELBDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            elbv2 = self.session.client("elbv2")
            paginator = elbv2.get_paginator("describe_load_balancers")
            for page in paginator.paginate():
                for lb in page["LoadBalancers"]:
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_ELB, name=lb["LoadBalancerName"],
                        project=self.region, location=lb.get("AvailabilityZones", [{}])[0].get("ZoneName", self.region),
                        terraform_resource_type="aws_lb",
                        terraform_resource_name=self.sanitize_name(lb["LoadBalancerName"]),
                        terraform_import_id=lb["LoadBalancerArn"],
                        attributes={"name": lb["LoadBalancerName"], "arn": lb["LoadBalancerArn"], "type": lb.get("Type", "application"), "scheme": lb.get("Scheme", "internet-facing"), "vpc_id": lb.get("VpcId", ""), "dns_name": lb.get("DNSName", ""), "state": lb.get("State", {}).get("Code", "")},
                    ))
            logger.info(f"Discovered {len(resources)} load balancers")
        except Exception as e:
            logger.error(f"Error discovering ELB: {e}")
        return resources
