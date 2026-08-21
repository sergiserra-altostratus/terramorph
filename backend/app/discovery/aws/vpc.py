"""AWS VPC, Subnet, and Security Group discovery with comprehensive attributes."""

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

                # Get DNS attributes
                dns_support = True
                dns_hostnames = False
                try:
                    resp = ec2.describe_vpc_attribute(VpcId=vpc["VpcId"], Attribute="enableDnsSupport")
                    dns_support = resp.get("EnableDnsSupport", {}).get("Value", True)
                    resp = ec2.describe_vpc_attribute(VpcId=vpc["VpcId"], Attribute="enableDnsHostnames")
                    dns_hostnames = resp.get("EnableDnsHostnames", {}).get("Value", False)
                except Exception:
                    pass

                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_VPC, name=name,
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_vpc",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=vpc["VpcId"],
                    attributes={
                        "vpc_id": vpc["VpcId"],
                        "cidr_block": vpc.get("CidrBlock", ""),
                        "instance_tenancy": vpc.get("InstanceTenancy", "default"),
                        "enable_dns_support": dns_support,
                        "enable_dns_hostnames": dns_hostnames,
                        "is_default": vpc.get("IsDefault", False),
                        "tags": {t["Key"]: t["Value"] for t in vpc.get("Tags", []) if t["Key"] != "Name"},
                    },
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
                    attributes={
                        "subnet_id": subnet["SubnetId"],
                        "vpc_id": subnet.get("VpcId", ""),
                        "cidr_block": subnet.get("CidrBlock", ""),
                        "availability_zone": subnet.get("AvailabilityZone", ""),
                        "map_public_ip_on_launch": subnet.get("MapPublicIpOnLaunch", False),
                        "assign_ipv6_address_on_creation": subnet.get("AssignIpv6AddressOnCreation", False),
                        "tags": {t["Key"]: t["Value"] for t in subnet.get("Tags", []) if t["Key"] != "Name"},
                    },
                ))

            # Security Groups
            for sg in ec2.describe_security_groups()["SecurityGroups"]:
                # Parse ingress rules
                ingress_rules = []
                for rule in sg.get("IpPermissions", []):
                    base_rule = {
                        "from_port": rule.get("FromPort", 0),
                        "to_port": rule.get("ToPort", 0),
                        "protocol": rule.get("IpProtocol", "-1"),
                        "description": "",
                    }
                    # CIDR-based rules
                    for ip_range in rule.get("IpRanges", []):
                        ingress_rules.append({
                            **base_rule,
                            "cidr_blocks": [ip_range["CidrIp"]],
                            "ipv6_cidr_blocks": [],
                            "security_groups": [],
                            "description": ip_range.get("Description", ""),
                        })
                    # IPv6 CIDR-based rules
                    for ip_range in rule.get("Ipv6Ranges", []):
                        ingress_rules.append({
                            **base_rule,
                            "cidr_blocks": [],
                            "ipv6_cidr_blocks": [ip_range["CidrIpv6"]],
                            "security_groups": [],
                            "description": ip_range.get("Description", ""),
                        })
                    # Security group-based rules
                    for sg_ref in rule.get("UserIdGroupPairs", []):
                        ingress_rules.append({
                            **base_rule,
                            "cidr_blocks": [],
                            "ipv6_cidr_blocks": [],
                            "security_groups": [sg_ref.get("GroupId", "")],
                            "description": sg_ref.get("Description", ""),
                        })
                    # If no specific targets, create generic rule
                    if not rule.get("IpRanges") and not rule.get("Ipv6Ranges") and not rule.get("UserIdGroupPairs"):
                        ingress_rules.append({**base_rule, "cidr_blocks": [], "ipv6_cidr_blocks": [], "security_groups": []})

                # Parse egress rules
                egress_rules = []
                for rule in sg.get("IpPermissionsEgress", []):
                    base_rule = {
                        "from_port": rule.get("FromPort", 0),
                        "to_port": rule.get("ToPort", 0),
                        "protocol": rule.get("IpProtocol", "-1"),
                        "description": "",
                    }
                    for ip_range in rule.get("IpRanges", []):
                        egress_rules.append({
                            **base_rule,
                            "cidr_blocks": [ip_range["CidrIp"]],
                            "ipv6_cidr_blocks": [],
                            "description": ip_range.get("Description", ""),
                        })
                    for ip_range in rule.get("Ipv6Ranges", []):
                        egress_rules.append({
                            **base_rule,
                            "cidr_blocks": [],
                            "ipv6_cidr_blocks": [ip_range["CidrIpv6"]],
                            "description": ip_range.get("Description", ""),
                        })
                    if not rule.get("IpRanges") and not rule.get("Ipv6Ranges"):
                        egress_rules.append({**base_rule, "cidr_blocks": ["0.0.0.0/0"], "ipv6_cidr_blocks": []})

                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_SECURITY_GROUP, name=sg["GroupName"],
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_security_group",
                    terraform_resource_name=self.sanitize_name(sg["GroupName"]),
                    terraform_import_id=sg["GroupId"],
                    attributes={
                        "group_id": sg["GroupId"],
                        "name": sg["GroupName"],
                        "description": sg.get("Description", ""),
                        "vpc_id": sg.get("VpcId", ""),
                        "ingress_rules": ingress_rules,
                        "egress_rules": egress_rules,
                        "tags": {t["Key"]: t["Value"] for t in sg.get("Tags", []) if t["Key"] != "Name"},
                    },
                ))

            logger.info(f"Discovered {len(resources)} VPC resources")
        except Exception as e:
            logger.error(f"Error discovering VPC: {e}")
        return resources
