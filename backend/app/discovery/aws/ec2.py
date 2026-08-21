"""AWS EC2 instance discovery with comprehensive attributes."""

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
                        # Skip terminated instances
                        if inst.get("State", {}).get("Name") == "terminated":
                            continue

                        name_tag = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), inst["InstanceId"])

                        # Get security group IDs
                        sg_ids = [sg["GroupId"] for sg in inst.get("SecurityGroups", [])]

                        # Get IAM instance profile
                        iam_profile = None
                        if inst.get("IamInstanceProfile"):
                            arn = inst["IamInstanceProfile"].get("Arn", "")
                            # Extract profile name from ARN
                            iam_profile = arn.split("/")[-1] if "/" in arn else arn

                        # Build root block device info
                        root_block_device = None
                        root_device_name = inst.get("RootDeviceName", "")
                        for bdm in inst.get("BlockDeviceMappings", []):
                            if bdm.get("DeviceName") == root_device_name and bdm.get("Ebs"):
                                ebs = bdm["Ebs"]
                                # Get volume details
                                try:
                                    vol_resp = ec2.describe_volumes(VolumeIds=[ebs["VolumeId"]])
                                    vol = vol_resp["Volumes"][0] if vol_resp["Volumes"] else {}
                                    root_block_device = {
                                        "volume_type": vol.get("VolumeType", "gp3"),
                                        "volume_size": vol.get("Size", 8),
                                        "encrypted": vol.get("Encrypted", False),
                                        "delete_on_termination": ebs.get("DeleteOnTermination", True),
                                    }
                                except Exception:
                                    root_block_device = {
                                        "volume_type": "gp3",
                                        "volume_size": 8,
                                        "encrypted": False,
                                        "delete_on_termination": ebs.get("DeleteOnTermination", True),
                                    }
                                break

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
                                "subnet_id": inst.get("SubnetId", ""),
                                "vpc_id": inst.get("VpcId", ""),
                                "key_name": inst.get("KeyName", ""),
                                "availability_zone": inst.get("Placement", {}).get("AvailabilityZone", ""),
                                "vpc_security_group_ids": sg_ids,
                                "iam_instance_profile": iam_profile,
                                "private_ip": inst.get("PrivateIpAddress", ""),
                                "public_ip": inst.get("PublicIpAddress", ""),
                                "monitoring": inst.get("Monitoring", {}).get("State") == "enabled",
                                "ebs_optimized": inst.get("EbsOptimized", False),
                                "tenancy": inst.get("Placement", {}).get("Tenancy", ""),
                                "associate_public_ip_address": inst.get("PublicIpAddress") is not None,
                                "root_block_device": root_block_device,
                                "tags": {t["Key"]: t["Value"] for t in inst.get("Tags", []) if t["Key"] != "Name"},
                            },
                        ))
            logger.info(f"Discovered {len(resources)} EC2 instances")
        except Exception as e:
            logger.error(f"Error discovering EC2: {e}")
        return resources
