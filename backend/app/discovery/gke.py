"""GKE Cluster discovery."""

import uuid

from google.cloud import container_v1

from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.gke")


class GKEDiscoverer(BaseDiscoverer):
    """Discovers GKE clusters."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover all GKE clusters in a project."""
        resources = []

        try:
            client = container_v1.ClusterManagerClient(credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"

            response = client.list_clusters(parent=parent)

            for cluster in response.clusters or []:
                location = cluster.location or cluster.zone or ""
                resource = DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.GKE_CLUSTER,
                    name=cluster.name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_container_cluster",
                    terraform_resource_name=self.sanitize_name(cluster.name),
                    terraform_import_id=(
                        f"projects/{project_id}/locations/{location}/clusters/{cluster.name}"
                    ),
                    attributes={
                        "location": location,
                        "network": cluster.network or "default",
                        "subnetwork": cluster.subnetwork or "default",
                        "initial_node_count": cluster.initial_node_count or 1,
                        "min_master_version": cluster.current_master_version or "",
                        "node_version": cluster.current_node_version or "",
                        "cluster_ipv4_cidr": cluster.cluster_ipv4_cidr or "",
                        "services_ipv4_cidr": cluster.services_ipv4_cidr or "",
                        "enable_autopilot": (
                            cluster.autopilot.enabled if cluster.autopilot else False
                        ),
                        "deletion_protection": (
                            cluster.deletion_protection
                            if hasattr(cluster, "deletion_protection")
                            else False
                        ),
                        "node_pools": [
                            {
                                "name": np.name,
                                "machine_type": (
                                    np.config.machine_type if np.config else "e2-medium"
                                ),
                                "node_count": np.initial_node_count or 1,
                                "disk_size_gb": np.config.disk_size_gb if np.config else 100,
                            }
                            for np in (cluster.node_pools or [])
                        ],
                        "labels": dict(cluster.resource_labels)
                        if cluster.resource_labels
                        else {},
                    },
                )
                resources.append(resource)

            logger.info(f"Discovered {len(resources)} GKE clusters in {project_id}")

        except Exception as e:
            logger.error(f"Error discovering GKE clusters in {project_id}: {e}")

        return resources
