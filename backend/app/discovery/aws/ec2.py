"""AWS EC2 instance discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.ec2")


class EC2Discoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            ec2 = self.session.client("ec2")
            paginator = ec2.get_paginator("describe_instances")
            for page in paginator.paginate():
                for reservation in page["Reservations"]:
                    for inst in reservation["Instances"]:
                        name_tag = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), inst["InstanceId"])
                        resources.append(DiscoveredResource(
                            id=str(uuid.uuid4()),
                            type=ResourceType.AWS_EC2_INSTANCE,
                            name=name_tag,
                            project=self.session.region_name,
                            location=inst.get("Placement", {}).get("AvailabilityZone", ""),
                            terraform_resource_type="aws_instance",
                            terraform_resource_name=self.sanitize_name(name_tag),
                            terraform_import_id=inst["InstanceId"],
                            attributes={
                                "instance_id": inst["InstanceId"],
                                "instance_type": inst.get("InstanceType", ""),
                                "ami": inst.get("ImageId", ""),
                                "state": inst.get("State", {}).get("Name", ""),
                                "subnet_id": inst.get("SubnetId", ""),
                                "vpc_id": inst.get("VpcId", ""),
                                "key_name": inst.get("KeyName", ""),
                                "tags": {t["Key"]: t["Value"] for t in inst.get("Tags", [])},
                            },
                        ))
            logger.info(f"Discovered {len(resources)} EC2 instances")
        except Exception as e:
            logger.error(f"Error discovering EC2: {e}")
        return resources
