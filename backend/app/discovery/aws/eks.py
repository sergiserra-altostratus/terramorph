"""AWS EKS cluster discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.eks")


class EKSDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            eks = self.session.client("eks")
            clusters = eks.list_clusters().get("clusters", [])
            for cluster_name in clusters:
                detail = eks.describe_cluster(name=cluster_name)["cluster"]
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_EKS_CLUSTER, name=cluster_name,
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_eks_cluster",
                    terraform_resource_name=self.sanitize_name(cluster_name),
                    terraform_import_id=cluster_name,
                    attributes={"name": cluster_name, "version": detail.get("version", ""), "role_arn": detail.get("roleArn", ""), "vpc_id": detail.get("resourcesVpcConfig", {}).get("vpcId", ""), "subnet_ids": detail.get("resourcesVpcConfig", {}).get("subnetIds", []), "endpoint": detail.get("endpoint", ""), "status": detail.get("status", "")},
                ))
            logger.info(f"Discovered {len(resources)} EKS clusters")
        except Exception as e:
            logger.error(f"Error discovering EKS: {e}")
        return resources
