"""Bulk Export discovery mode using gcloud beta resource-config bulk-export.

Executes gcloud CLI to extract resources in Terraform format directly from
GCP Cloud Asset API. More precise than API discovery but requires gcloud CLI.
"""

import asyncio
import os
import re
import shutil
import subprocess
import time
import uuid
from typing import Any

from app.core.logging import get_logger
from app.models.discovery import JobProgress, JobStatus
from app.models.resources import DiscoveredResource, ResourceType

logger = get_logger("bulk_export")

# Map GCP resource type names to our ResourceType enum
BULK_EXPORT_RESOURCE_TYPES = [
    "ArtifactRegistryRepository",
    "BigQueryDataset",
    "ComputeAddress",
    "ComputeBackendService",
    "ComputeDisk",
    "ComputeFirewall",
    "ComputeForwardingRule",
    "ComputeHealthCheck",
    "ComputeImage",
    "ComputeInstance",
    "ComputeInstanceGroup",
    "ComputeInstanceTemplate",
    "ComputeNetwork",
    "ComputeReservation",
    "ComputeRoute",
    "ComputeRouter",
    "ComputeSSLPolicy",
    "ComputeSecurityPolicy",
    "ComputeSnapshot",
    "ComputeSubnetwork",
    "ComputeTargetHTTPProxy",
    "ComputeTargetHTTPSProxy",
    "ComputeURLMap",
    "ComputeVPNGateway",
    "ContainerCluster",
    "ContainerNodePool",
    "DNSManagedZone",
    "DNSPolicy",
    "IAMCustomRole",
    "IAMServiceAccount",
    "LoggingLogSink",
    "MonitoringAlertPolicy",
    "PubSubSubscription",
    "PubSubTopic",
    "RedisInstance",
    "SecretManagerSecret",
    "SpannerInstance",
    "SQLInstance",
    "StorageBucket",
]

# In-memory job storage for bulk export jobs
_bulk_jobs: dict[str, dict[str, Any]] = {}


def is_gcloud_available() -> bool:
    """Check if gcloud CLI is available."""
    return shutil.which("gcloud") is not None


def _setup_gcloud_env() -> None:
    """Configure gcloud to use the same ADC credentials as the Python SDKs.

    Sets CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE so gcloud commands
    automatically use the mounted ADC file without needing 'gcloud auth login'.
    """
    cred_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if cred_file and os.path.exists(cred_file):
        os.environ["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] = cred_file
        logger.info(f"gcloud configured to use ADC from {cred_file}")

        # Try to detect and set project
        try:
            import json
            with open(cred_file) as f:
                cred_data = json.load(f)
            project = cred_data.get("quota_project_id") or cred_data.get("project_id")
            if project:
                os.environ["CLOUDSDK_CORE_PROJECT"] = project
                logger.info(f"gcloud default project set to {project}")
        except Exception:
            pass


# Setup on module load
_setup_gcloud_env()


def get_bulk_job_status(job_id: str) -> dict | None:
    """Get bulk export job status."""
    return _bulk_jobs.get(job_id)


def get_bulk_job_results(job_id: str) -> dict | None:
    """Get bulk export job results."""
    job = _bulk_jobs.get(job_id)
    if not job:
        return None
    return {
        "job_id": job_id,
        "status": job["status"],
        "resources": job.get("resources", []),
        "tf_files": job.get("tf_files", {}),
        "error": job.get("error"),
    }


async def start_bulk_export(project_id: str, resource_types: list[str] | None = None) -> str:
    """Start a bulk export discovery job.

    Args:
        project_id: GCP project to export from.
        resource_types: Optional list of resource types to export.
                       If None, exports all supported types.

    Returns:
        Job ID for tracking.
    """
    job_id = str(uuid.uuid4())
    types_to_export = resource_types or BULK_EXPORT_RESOURCE_TYPES

    _bulk_jobs[job_id] = {
        "status": JobStatus.RUNNING,
        "progress": JobProgress(
            total=len(types_to_export),
            completed=0,
            message="Starting bulk export...",
        ),
        "resources": [],
        "tf_files": {},
        "created_at": time.time(),
        "error": None,
    }

    asyncio.create_task(_run_bulk_export(job_id, project_id, types_to_export))
    return job_id


async def _run_bulk_export(job_id: str, project_id: str, resource_types: list[str]) -> None:
    """Execute bulk export for each resource type."""
    job = _bulk_jobs[job_id]
    all_tf_content: dict[str, str] = {}
    all_resources: list[dict] = []

    for idx, resource_type in enumerate(resource_types):
        job["progress"] = JobProgress(
            total=len(resource_types),
            completed=idx,
            current_type=resource_type,
            message=f"Exporting {resource_type}...",
        )

        try:
            result = await asyncio.to_thread(
                _export_resource_type, project_id, resource_type
            )

            if result["content"]:
                filename = _get_filename_for_type(resource_type)
                if filename in all_tf_content:
                    all_tf_content[filename] += "\n\n" + result["content"]
                else:
                    all_tf_content[filename] = result["content"]

                all_resources.extend(result["resources"])

        except Exception as e:
            logger.warning(f"Bulk export failed for {resource_type}: {e}")

    job["tf_files"] = all_tf_content
    job["resources"] = all_resources
    job["status"] = JobStatus.COMPLETED
    job["progress"] = JobProgress(
        total=len(resource_types),
        completed=len(resource_types),
        message=f"Bulk export complete. Found {len(all_resources)} resources across {len(all_tf_content)} files.",
    )

    logger.info(f"Bulk export {job_id}: {len(all_resources)} resources in {len(all_tf_content)} files")


def _export_resource_type(project_id: str, resource_type: str) -> dict:
    """Run gcloud bulk-export for a single resource type.

    Returns:
        Dict with 'content' (raw HCL) and 'resources' (parsed resource list).
    """
    # Build environment with ADC credential override for gcloud
    env = os.environ.copy()
    cred_file = env.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if cred_file:
        env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] = cred_file

    result = subprocess.run(
        [
            "gcloud", "beta", "resource-config", "bulk-export",
            f"--project={project_id}",
            f"--resource-types={resource_type}",
            "--resource-format=terraform",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )

    content = result.stdout.strip()
    if not content:
        return {"content": "", "resources": []}

    # Parse resources from the HCL output
    resources = _parse_resources_from_hcl(content, project_id, resource_type)

    return {"content": content, "resources": resources}


def _parse_resources_from_hcl(hcl_content: str, project_id: str, resource_type: str) -> list[dict]:
    """Parse resource blocks and import comments from bulk export HCL."""
    resources = []

    # Find resource blocks: resource "type" "name" { ... }
    resource_pattern = re.compile(
        r'resource\s+"([^"]+)"\s+"([^"]+)"',
        re.MULTILINE,
    )

    # Find import comments: # terraform import type.name import_id
    import_pattern = re.compile(
        r'#\s*terraform\s+import\s+(\S+)\s+(.+)',
        re.MULTILINE,
    )

    imports = {m.group(1): m.group(2).strip() for m in import_pattern.finditer(hcl_content)}

    for match in resource_pattern.finditer(hcl_content):
        tf_type = match.group(1)
        tf_name = match.group(2)
        resource_id = f"{tf_type}.{tf_name}"
        import_id = imports.get(resource_id, "")

        resources.append({
            "id": str(uuid.uuid4()),
            "type": resource_type,
            "name": tf_name,
            "project": project_id,
            "terraform_resource_type": tf_type,
            "terraform_resource_name": tf_name,
            "terraform_import_id": import_id,
        })

    return resources


def _get_filename_for_type(resource_type: str) -> str:
    """Map a GCP resource type to an output filename."""
    mapping = {
        "ComputeInstance": "compute_instance.tf",
        "ComputeNetwork": "network.tf",
        "ComputeSubnetwork": "network.tf",
        "ComputeFirewall": "firewall.tf",
        "ComputeForwardingRule": "load_balancer.tf",
        "ComputeBackendService": "load_balancer.tf",
        "ComputeTargetHTTPProxy": "load_balancer.tf",
        "ComputeTargetHTTPSProxy": "load_balancer.tf",
        "ComputeURLMap": "load_balancer.tf",
        "ComputeHealthCheck": "healthcheck.tf",
        "ComputeDisk": "compute_disk.tf",
        "ComputeImage": "compute_image.tf",
        "ComputeSnapshot": "compute_snapshot.tf",
        "ComputeInstanceGroup": "instance_group.tf",
        "ComputeInstanceTemplate": "instance_template.tf",
        "ComputeAddress": "addresses.tf",
        "ComputeRoute": "routes.tf",
        "ComputeRouter": "router.tf",
        "ComputeSSLPolicy": "ssl.tf",
        "ComputeSecurityPolicy": "armor.tf",
        "ComputeReservation": "reservations.tf",
        "ComputeVPNGateway": "vpn.tf",
        "ContainerCluster": "gke.tf",
        "ContainerNodePool": "gke.tf",
        "StorageBucket": "storage.tf",
        "SQLInstance": "sql.tf",
        "BigQueryDataset": "bigquery.tf",
        "DNSManagedZone": "dns.tf",
        "DNSPolicy": "dns.tf",
        "PubSubTopic": "pubsub.tf",
        "PubSubSubscription": "pubsub.tf",
        "IAMServiceAccount": "iam.tf",
        "IAMCustomRole": "iam.tf",
        "RedisInstance": "redis.tf",
        "SpannerInstance": "spanner.tf",
        "SecretManagerSecret": "secrets.tf",
        "LoggingLogSink": "logging.tf",
        "MonitoringAlertPolicy": "monitoring.tf",
        "ArtifactRegistryRepository": "artifact_registry.tf",
    }
    return mapping.get(resource_type, f"{resource_type.lower()}.tf")
