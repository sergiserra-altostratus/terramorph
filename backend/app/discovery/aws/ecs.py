"""AWS ECS cluster and service discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.ecs")


class ECSDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("ecs")
            cluster_arns = client.list_clusters().get("clusterArns", [])
            if cluster_arns:
                clusters = client.describe_clusters(clusters=cluster_arns).get("clusters", [])
                for cluster in clusters:
                    name = cluster["clusterName"]
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_ECS_CLUSTER, name=name,
                        project=self.region, location=self.region,
                        terraform_resource_type="aws_ecs_cluster",
                        terraform_resource_name=self.sanitize_name(name),
                        terraform_import_id=cluster["clusterArn"],
                        attributes={
                            "name": name,
                            "arn": cluster["clusterArn"],
                            "status": cluster.get("status", ""),
                            "running_tasks": cluster.get("runningTasksCount", 0),
                            "active_services": cluster.get("activeServicesCount", 0),
                            "capacity_providers": cluster.get("capacityProviders", []),
                        },
                    ))
            logger.info(f"Discovered {len(resources)} ECS clusters")
        except Exception as e:
            logger.error(f"Error discovering ECS: {e}")
        return resources
