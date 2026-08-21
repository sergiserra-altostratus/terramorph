"""AWS S3 bucket discovery with comprehensive attributes."""

import uuid
from app.core.logging import get_logger
from app.discovery.aws.base import AWSBaseDiscoverer
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("aws.discovery.s3")


class S3Discoverer(AWSBaseDiscoverer):
    async def discover(self) -> list[DiscoveredResource]:
        resources = []
        try:
            s3 = self.session.client("s3")
            buckets = s3.list_buckets().get("Buckets", [])

            for bucket in buckets:
                bucket_name = bucket["Name"]

                # Filter by region (only include buckets in the configured region)
                try:
                    location = s3.get_bucket_location(Bucket=bucket_name)
                    bucket_region = location.get("LocationConstraint") or "us-east-1"
                    if bucket_region != self.region:
                        continue
                except Exception:
                    continue

                # Get versioning
                versioning = None
                try:
                    v = s3.get_bucket_versioning(Bucket=bucket_name)
                    status = v.get("Status")
                    if status:
                        versioning = {"status": status}
                except Exception:
                    pass

                # Get encryption
                encryption = None
                try:
                    enc = s3.get_bucket_encryption(Bucket=bucket_name)
                    rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
                    if rules:
                        default_rule = rules[0].get("ApplyServerSideEncryptionByDefault", {})
                        encryption = {
                            "sse_algorithm": default_rule.get("SSEAlgorithm", "AES256"),
                            "kms_master_key_id": default_rule.get("KMSMasterKeyID"),
                            "bucket_key_enabled": rules[0].get("BucketKeyEnabled", False),
                        }
                except s3.exceptions.ClientError:
                    pass
                except Exception:
                    pass

                # Get public access block
                public_access_block = None
                try:
                    pab = s3.get_public_access_block(Bucket=bucket_name)
                    config = pab.get("PublicAccessBlockConfiguration", {})
                    public_access_block = {
                        "block_public_acls": config.get("BlockPublicAcls", True),
                        "block_public_policy": config.get("BlockPublicPolicy", True),
                        "ignore_public_acls": config.get("IgnorePublicAcls", True),
                        "restrict_public_buckets": config.get("RestrictPublicBuckets", True),
                    }
                except Exception:
                    pass

                # Get logging
                logging_config = None
                try:
                    log = s3.get_bucket_logging(Bucket=bucket_name)
                    log_enabled = log.get("LoggingEnabled")
                    if log_enabled:
                        logging_config = {
                            "target_bucket": log_enabled.get("TargetBucket", ""),
                            "target_prefix": log_enabled.get("TargetPrefix", ""),
                        }
                except Exception:
                    pass

                # Get tags
                tags = {}
                try:
                    tag_resp = s3.get_bucket_tagging(Bucket=bucket_name)
                    tags = {t["Key"]: t["Value"] for t in tag_resp.get("TagSet", [])}
                except Exception:
                    pass

                resources.append(DiscoveredResource(
                    id=str(uuid.uuid4()),
                    type=ResourceType.AWS_S3_BUCKET,
                    name=bucket_name,
                    project=self.region,
                    location=bucket_region,
                    terraform_resource_type="aws_s3_bucket",
                    terraform_resource_name=self.sanitize_name(bucket_name),
                    terraform_import_id=bucket_name,
                    attributes={
                        "bucket": bucket_name,
                        "versioning": versioning,
                        "server_side_encryption": encryption,
                        "public_access_block": public_access_block,
                        "logging": logging_config,
                        "tags": tags,
                    },
                ))

            logger.info(f"Discovered {len(resources)} S3 buckets")
        except Exception as e:
            logger.error(f"Error discovering S3: {e}")
        return resources
