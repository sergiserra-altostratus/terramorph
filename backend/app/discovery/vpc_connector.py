"""VPC Access Connector (Serverless VPC Access) discovery."""

import uuid
from googleapiclient.discovery import build
from app.core.logging import get_logger
from app.discovery.base import BaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("discovery.vpc_connector")


class VPCAccessConnectorDiscoverer(BaseDiscoverer):
    """Discovers Serverless VPC Access Connectors."""

    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        resources = []
        try:
            service = build("vpcaccess", "v1", credentials=self.credentials)
            parent = f"projects/{project_id}/locations/-"
            response = service.projects().locations().connectors().list(parent=parent).execute()
            for conn in response.get("connectors", []):
                name = conn["name"].split("/")[-1]
                location = conn["name"].split("/locations/")[1].split("/")[0]
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.VPC_CONNECTOR,
                    name=name,
                    project=project_id,
                    location=location,
                    terraform_resource_type="google_vpc_access_connector",
                    terraform_resource_name=self.sanitize_name(name),
                    terraform_import_id=conn["name"],
                    attributes={
                        "region": location,
                        "network": conn.get("network", ""),
                        "ip_cidr_range": conn.get("ipCidrRange", ""),
                        "min_throughput": conn.get("minThroughput", 200),
                        "max_throughput": conn.get("maxThroughput", 300),
                        "machine_type": conn.get("machineType", "e2-micro"),
                    },
                ))
            logger.info(f"Discovered {len(resources)} VPC connectors in {project_id}")
        except Exception as e:
            logger.error(f"Error discovering VPC connectors in {project_id}: {e}")
        return resources
