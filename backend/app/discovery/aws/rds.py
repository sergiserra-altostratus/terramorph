"""AWS RDS instance discovery."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.rds")


class RDSDiscoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            rds = self.session.client("rds")
            paginator = rds.get_paginator("describe_db_instances")
            for page in paginator.paginate():
                for db in page["DBInstances"]:
                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()), type=ResourceType.AWS_RDS_INSTANCE, name=db["DBInstanceIdentifier"],
                        project=self.region, location=db.get("AvailabilityZone", ""),
                        terraform_resource_type="aws_db_instance",
                        terraform_resource_name=self.sanitize_name(db["DBInstanceIdentifier"]),
                        terraform_import_id=db["DBInstanceIdentifier"],
                        attributes={"identifier": db["DBInstanceIdentifier"], "engine": db.get("Engine", ""), "engine_version": db.get("EngineVersion", ""), "instance_class": db.get("DBInstanceClass", ""), "allocated_storage": db.get("AllocatedStorage", 20), "storage_type": db.get("StorageType", "gp2"), "multi_az": db.get("MultiAZ", False), "publicly_accessible": db.get("PubliclyAccessible", False)},
                    ))
            logger.info(f"Discovered {len(resources)} RDS instances")
        except Exception as e:
            logger.error(f"Error discovering RDS: {e}")
        return resources
