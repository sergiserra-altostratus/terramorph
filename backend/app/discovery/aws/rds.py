"""AWS RDS instance discovery with comprehensive attributes."""

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
                    name = db["DBInstanceIdentifier"]
                    sg_ids = [sg["VpcSecurityGroupId"] for sg in db.get("VpcSecurityGroups", [])]

                    # Get tags
                    tags = {}
                    try:
                        tag_resp = rds.list_tags_for_resource(ResourceName=db["DBInstanceArn"])
                        tags = {t["Key"]: t["Value"] for t in tag_resp.get("TagList", [])}
                    except Exception:
                        pass

                    resources.append(DiscoveredResource(
                        id=str(uuid.uuid4()),
                        type=ResourceType.AWS_RDS_INSTANCE,
                        name=name,
                        project=self.region,
                        location=db.get("AvailabilityZone", ""),
                        terraform_resource_type="aws_db_instance",
                        terraform_resource_name=self.sanitize_name(name),
                        terraform_import_id=name,
                        attributes={
                            "identifier": name,
                            "engine": db.get("Engine", ""),
                            "engine_version": db.get("EngineVersion", ""),
                            "instance_class": db.get("DBInstanceClass", ""),
                            "allocated_storage": db.get("AllocatedStorage", 20),
                            "max_allocated_storage": db.get("MaxAllocatedStorage"),
                            "storage_type": db.get("StorageType", "gp2"),
                            "storage_encrypted": db.get("StorageEncrypted", False),
                            "kms_key_id": db.get("KmsKeyId", ""),
                            "db_name": db.get("DBName", ""),
                            "username": db.get("MasterUsername", ""),
                            "port": db.get("Endpoint", {}).get("Port"),
                            "multi_az": db.get("MultiAZ", False),
                            "availability_zone": db.get("AvailabilityZone", ""),
                            "db_subnet_group_name": db.get("DBSubnetGroup", {}).get("DBSubnetGroupName", ""),
                            "vpc_security_group_ids": sg_ids,
                            "parameter_group_name": db.get("DBParameterGroups", [{}])[0].get("DBParameterGroupName", "") if db.get("DBParameterGroups") else "",
                            "publicly_accessible": db.get("PubliclyAccessible", False),
                            "backup_retention_period": db.get("BackupRetentionPeriod", 7),
                            "backup_window": db.get("PreferredBackupWindow", ""),
                            "maintenance_window": db.get("PreferredMaintenanceWindow", ""),
                            "auto_minor_version_upgrade": db.get("AutoMinorVersionUpgrade", True),
                            "deletion_protection": db.get("DeletionProtection", False),
                            "skip_final_snapshot": True,
                            "copy_tags_to_snapshot": db.get("CopyTagsToSnapshot", False),
                            "performance_insights_enabled": db.get("PerformanceInsightsEnabled", False),
                            "monitoring_interval": db.get("MonitoringInterval", 0),
                            "enabled_cloudwatch_logs_exports": db.get("EnabledCloudwatchLogsExports", []),
                            "tags": tags,
                        },
                    ))
            logger.info(f"Discovered {len(resources)} RDS instances")
        except Exception as e:
            logger.error(f"Error discovering RDS: {e}")
        return resources
