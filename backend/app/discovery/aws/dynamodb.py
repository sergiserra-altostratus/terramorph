"""AWS DynamoDB table discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.dynamodb")


class DynamoDBDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            client = self.session.client("dynamodb")
            paginator = client.get_paginator("list_tables")
            for page in paginator.paginate():
                for table_name in page.get("TableNames", []):
                    detail = client.describe_table(TableName=table_name)["Table"]
                    key_schema = detail.get("KeySchema", [])
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_DYNAMODB, name=table_name,
                        project=self.region, location=self.region,
                        terraform_resource_type="aws_dynamodb_table",
                        terraform_resource_name=self.sanitize_name(table_name),
                        terraform_import_id=table_name,
                        attributes={
                            "name": table_name,
                            "billing_mode": detail.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED"),
                            "hash_key": next((k["AttributeName"] for k in key_schema if k["KeyType"] == "HASH"), ""),
                            "range_key": next((k["AttributeName"] for k in key_schema if k["KeyType"] == "RANGE"), ""),
                            "read_capacity": detail.get("ProvisionedThroughput", {}).get("ReadCapacityUnits", 5),
                            "write_capacity": detail.get("ProvisionedThroughput", {}).get("WriteCapacityUnits", 5),
                            "status": detail.get("TableStatus", ""),
                        },
                    ))
            logger.info(f"Discovered {len(resources)} DynamoDB tables")
        except Exception as e:
            logger.error(f"Error discovering DynamoDB: {e}")
        return resources
