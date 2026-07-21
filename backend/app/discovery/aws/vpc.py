"""AWS VPC, Subnet, and Security Group discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.vpc")


class VPCDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            ec2 = self.session.client("ec2")

            # VPCs
            for vpc in ec2.describe_vpcs()["Vpcs"]:
                name = next((t["Value"] for t in vpc.get("Tags", []) if t["Key"] == "Name"), vpc["VpcId"])
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_VPC, name=name,
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_vpc",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=vpc["VpcId"],
                    attributes={"vpc_id": vpc["VpcId"], "cidr_block": vpc.get("CidrBlock", ""), "is_default": vpc.get("IsDefault", False), "tags": {t["Key"]: t["Value"] for t in vpc.get("Tags", [])}},
                ))

            # Subnets
            for subnet in ec2.describe_subnets()["Subnets"]:
                name = next((t["Value"] for t in subnet.get("Tags", []) if t["Key"] == "Name"), subnet["SubnetId"])
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_SUBNET, name=name,
                    project=self.region, location=subnet.get("AvailabilityZone", ""),
                    terraform_resource_type="aws_subnet",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=subnet["SubnetId"],
                    attributes={"subnet_id": subnet["SubnetId"], "vpc_id": subnet.get("VpcId", ""), "cidr_block": subnet.get("CidrBlock", ""), "availability_zone": subnet.get("AvailabilityZone", ""), "map_public_ip": subnet.get("MapPublicIpOnLaunch", False)},
                ))

            # Security Groups
            for sg in ec2.describe_security_groups()["SecurityGroups"]:
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_SECURITY_GROUP, name=sg["GroupName"],
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_security_group",
                    terraform_resource_name=self.sanitize_name(sg["GroupName"]),
                    terraform_import_id=sg["GroupId"],
                    attributes={"group_id": sg["GroupId"], "vpc_id": sg.get("VpcId", ""), "description": sg.get("Description", ""), "ingress_rules": len(sg.get("IpPermissions", [])), "egress_rules": len(sg.get("IpPermissionsEgress", []))},
                ))

            logger.info(f"Discovered {len(resources)} VPC resources")
        except Exception as e:
            logger.error(f"Error discovering VPC: {e}")
        return resources
