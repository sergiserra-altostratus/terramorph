"""AWS Discovery orchestrator — coordinates all AWS discoverers."""

import asyncio
import time
import uuid
from typing import Any

from app.core.logging import get_logger
from app.discovery.aws.cloudfront import CloudFrontDiscoverer
from app.discovery.aws.ec2 import EC2Discoverer
from app.discovery.aws.eks import EKSDiscoverer
from app.discovery.aws.elb import ELBDiscoverer
from app.discovery.aws.iam import IAMDiscoverer
from app.discovery.aws.lambda_fn import LambdaDiscoverer
from app.discovery.aws.rds import RDSDiscoverer
from app.discovery.aws.route53 import Route53Discoverer
from app.discovery.aws.s3 import S3Discoverer
from app.discovery.aws.vpc import VPCDiscoverer
from app.models.discovery import JobProgress, JobStatus
from app.models.resources import DiscoveredResource, ResourceType
from app.services.aws_credentials import get_boto3_session, is_aws_configured

logger = get_logger("aws.orchestrator")

# AWS job storage
_aws_jobs: dict[str, dict[str, Any]] = {}

AWS_DISCOVERER_MAP = {
    ResourceType.AWS_EC2_INSTANCE: EC2Discoverer,
    ResourceType.AWS_VPC: VPCDiscoverer,
    ResourceType.AWS_S3_BUCKET: S3Discoverer,
    ResourceType.AWS_RDS_INSTANCE: RDSDiscoverer,
    ResourceType.AWS_EKS_CLUSTER: EKSDiscoverer,
    ResourceType.AWS_LAMBDA: LambdaDiscoverer,
    ResourceType.AWS_IAM_ROLE: IAMDiscoverer,
    ResourceType.AWS_ROUTE53_ZONE: Route53Discoverer,
    ResourceType.AWS_CLOUDFRONT: CloudFrontDiscoverer,
    ResourceType.AWS_ELB: ELBDiscoverer,
}

AWS_RESOURCE_TYPE_TEMPLATE_MAP = {
    ResourceType.AWS_EC2_INSTANCE: "aws/ec2_instance.tf.j2",
    ResourceType.AWS_VPC: "aws/vpc.tf.j2",
    ResourceType.AWS_SUBNET: "aws/subnet.tf.j2",
    ResourceType.AWS_SECURITY_GROUP: "aws/security_group.tf.j2",
    ResourceType.AWS_S3_BUCKET: "aws/s3_bucket.tf.j2",
    ResourceType.AWS_RDS_INSTANCE: "aws/rds_instance.tf.j2",
    ResourceType.AWS_EKS_CLUSTER: "aws/eks_cluster.tf.j2",
    ResourceType.AWS_LAMBDA: "aws/lambda_function.tf.j2",
    ResourceType.AWS_IAM_ROLE: "aws/iam_role.tf.j2",
    ResourceType.AWS_ROUTE53_ZONE: "aws/route53_zone.tf.j2",
    ResourceType.AWS_CLOUDFRONT: "aws/cloudfront.tf.j2",
    ResourceType.AWS_ELB: "aws/elb.tf.j2",
}

AWS_RESOURCE_TYPE_FILE_MAP = {
    ResourceType.AWS_EC2_INSTANCE: "ec2.tf",
    ResourceType.AWS_VPC: "vpc.tf",
    ResourceType.AWS_SUBNET: "vpc.tf",
    ResourceType.AWS_SECURITY_GROUP: "security_groups.tf",
    ResourceType.AWS_S3_BUCKET: "s3.tf",
    ResourceType.AWS_RDS_INSTANCE: "rds.tf",
    ResourceType.AWS_EKS_CLUSTER: "eks.tf",
    ResourceType.AWS_LAMBDA: "lambda.tf",
    ResourceType.AWS_IAM_ROLE: "iam.tf",
    ResourceType.AWS_ROUTE53_ZONE: "route53.tf",
    ResourceType.AWS_CLOUDFRONT: "cloudfront.tf",
    ResourceType.AWS_ELB: "elb.tf",
}


def get_aws_job_status(job_id: str) -> dict | None:
    return _aws_jobs.get(job_id)


def get_aws_job_results(job_id: str) -> dict | None:
    job = _aws_jobs.get(job_id)
    if not job:
        return None
    return {
        "job_id": job_id,
        "status": job["status"],
        "resources": job.get("resources", []),
        "summary": _build_summary(job.get("resources", [])),
    }


def _build_summary(resources: list[DiscoveredResource]) -> dict:
    summary = {}
    for rt in ResourceType:
        if rt.value.startswith("aws_"):
            count = sum(1 for r in resources if r.type == rt)
            if count > 0:
                summary[rt.value] = count
    return summary


async def start_aws_discovery(resource_types: list[ResourceType]) -> str:
    """Start AWS resource discovery."""
    if not is_aws_configured():
        raise ValueError("AWS credentials not configured. Go to Settings.")

    job_id = str(uuid.uuid4())
    _aws_jobs[job_id] = {
        "status": JobStatus.RUNNING,
        "progress": JobProgress(total=len(resource_types), completed=0, message="Starting AWS discovery..."),
        "resources": [],
        "created_at": time.time(),
    }

    asyncio.create_task(_run_aws_discovery(job_id, resource_types))
    return job_id


async def _run_aws_discovery(job_id: str, resource_types: list[ResourceType]) -> None:
    job = _aws_jobs[job_id]
    try:
        session = get_boto3_session()
        all_resources: list[DiscoveredResource] = []

        for idx, rt in enumerate(resource_types):
            discoverer_class = AWS_DISCOVERER_MAP.get(rt)
            if not discoverer_class:
                continue

            job["progress"] = JobProgress(
                total=len(resource_types), completed=idx,
                current_type=rt.value, message=f"Discovering {rt.value}...",
            )

            discoverer = discoverer_class(session)
            resources = await discoverer.discover()
            all_resources.extend(resources)

        job["resources"] = all_resources
        job["status"] = JobStatus.COMPLETED
        job["progress"] = JobProgress(
            total=len(resource_types), completed=len(resource_types),
            message=f"Discovery complete. Found {len(all_resources)} AWS resources.",
        )
        logger.info(f"AWS job {job_id}: {len(all_resources)} resources found")

    except Exception as e:
        job["status"] = JobStatus.FAILED
        job["progress"].message = f"Discovery failed: {str(e)}"
        logger.error(f"AWS job {job_id} failed: {e}")
