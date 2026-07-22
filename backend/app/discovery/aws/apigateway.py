"""AWS API Gateway (REST APIs) discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.apigateway")


class APIGatewayDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("apigateway")
            apis = client.get_rest_apis().get("items", [])
            for api in apis:
                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()), type=ResourceType.AWS_API_GATEWAY, name=api["name"],
                    project=self.region, location=self.region,
                    terraform_resource_type="aws_api_gateway_rest_api",
                    terraform_resource_name=self.sanitize_name(api["name"]),
                    terraform_import_id=api["id"],
                    attributes={
                        "name": api["name"],
                        "api_id": api["id"],
                        "description": api.get("description", ""),
                        "endpoint_type": api.get("endpointConfiguration", {}).get("types", ["EDGE"])[0],
                    },
                ))
            logger.info(f"Discovered {len(resources)} API Gateways")
        except Exception as e:
            logger.error(f"Error discovering API Gateway: {e}")
        return resources
