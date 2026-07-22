"""AWS Elastic IP discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.eip")


class ElasticIPDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("ec2")
            addresses = client.describe_addresses().get("Addresses", [])
            for addr in addresses:
                name = next((t["Value"] for t in addr.get("Tags", []) if t["Key"] == "Name"), addr.get("AllocationId", ""))
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_ELASTIC_IP, name=name,
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_eip",
                    terraform_resource_name=self.sanitize_name(name or addr.get("AllocationId", "")),
                    terraform_import_id=addr.get("AllocationId", ""),
                    attributes={
                        "allocation_id": addr.get("AllocationId", ""),
                        "public_ip": addr.get("PublicIp", ""),
                        "instance_id": addr.get("InstanceId", ""),
                        "domain": addr.get("Domain", "vpc"),
                    },
                ))
            logger.info(f"Discovered {len(resources)} Elastic IPs")
        except Exception as e:
            logger.error(f"Error discovering Elastic IPs: {e}")
        return resources
