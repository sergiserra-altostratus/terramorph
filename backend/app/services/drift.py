"""Drift detection and AI-powered auto-fix service.

Executes terraform plan against generated code + imported state,
detects drift, and uses AI to iteratively correct it until
'No changes. Your infrastructure matches the configuration.'

Requirements:
- AI provider must be configured in Settings
- Backend state (GCS bucket) must be specified
"""

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.services.ai_settings import get_active_config, is_ai_configured

logger = get_logger("drift")

# In-memory drift job storage
_drift_jobs: dict[str, dict[str, Any]] = {}

MAX_FIX_ITERATIONS = 10

FIX_DRIFT_PROMPT = """There is drift in the following Terraform file. You must fix the drift to achieve
'No changes. Your infrastructure matches the configuration.' state.

This may require adding, removing, or modifying attribute values. Inspect the terraform plan output
and act accordingly.

Rules:
- If a resource is planned to be destroyed and recreated, change ONLY the parameters that force the replacement.
- If replacement is forced by a value (shows "# forces replacement"), fix ONLY that parameter.
- Do NOT add lifecycle blocks with ignore_changes.
- Do NOT add comments or explanations.
- Preserve proper HCL formatting.
- Return ONLY the corrected Terraform code, nothing else.

Terraform File:
```hcl
{tf_content}
```

Terraform Plan Output:
```
{plan_output}
```

Return ONLY the fixed Terraform code. No markdown, no backticks, no explanations."""


@dataclass
class DriftResult:
    """Result of a single drift check."""

    has_drift: bool
    plan_output: str
    resources_changed: int
    resources_added: int
    resources_destroyed: int


def _run_terraform(args: list[str], cwd: str, timeout: int = 120) -> tuple[str, str, int]:
    """Run a terraform command and return stdout, stderr, returncode."""
    result = subprocess.run(
        ["terraform"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    # Strip ANSI escape codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    stdout = ansi_escape.sub("", result.stdout)
    stderr = ansi_escape.sub("", result.stderr)
    return stdout, stderr, result.returncode


def _parse_plan_output(stdout: str, stderr: str) -> DriftResult:
    """Parse terraform plan output to detect drift."""
    combined = stdout + "\n" + stderr
    no_changes = "No changes. Your infrastructure matches the configuration" in combined

    # Count changes
    changed = len(re.findall(r"# .+ will be updated", combined))
    added = len(re.findall(r"# .+ will be created", combined))
    destroyed = len(re.findall(r"# .+ will be destroyed", combined))

    return DriftResult(
        has_drift=not no_changes and (changed + added + destroyed > 0 or "Error" in stderr),
        plan_output=combined,
        resources_changed=changed,
        resources_added=added,
        resources_destroyed=destroyed,
    )


def get_drift_job_status(job_id: str) -> dict | None:
    """Get drift job status."""
    return _drift_jobs.get(job_id)


async def start_drift_detection(
    tf_files: dict[str, str],
    bucket: str,
    prefix: str,
    project_id: str,
) -> str:
    """Start a drift detection and auto-fix job.

    Args:
        tf_files: Dict of filename → HCL content (the generated terraform files).
        bucket: GCS bucket for remote state.
        prefix: State prefix in the bucket.
        project_id: GCP project ID.

    Returns:
        Job ID for tracking progress.
    """
    job_id = str(uuid.uuid4())
    _drift_jobs[job_id] = {
        "status": "running",
        "progress": {"iteration": 0, "max_iterations": MAX_FIX_ITERATIONS, "message": "Initializing..."},
        "started_at": time.time(),
        "result": None,
        "error": None,
        "fix_history": [],
    }

    asyncio.create_task(_run_drift_detection(job_id, tf_files, bucket, prefix, project_id))
    return job_id


async def _run_drift_detection(
    job_id: str,
    tf_files: dict[str, str],
    bucket: str,
    prefix: str,
    project_id: str,
) -> None:
    """Execute drift detection and auto-fix loop."""
    job = _drift_jobs[job_id]

    # Get AI config
    ai_config = get_active_config()
    if not ai_config:
        job["status"] = "failed"
        job["error"] = "No AI provider configured. Configure one in Settings."
        return

    # Create temp directory with terraform files
    work_dir = tempfile.mkdtemp(prefix="terramorph-drift-")

    try:
        # Write all terraform files
        for filename, content in tf_files.items():
            filepath = os.path.join(work_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)

        # Write backend.tf
        backend_content = f'''terraform {{
  backend "gcs" {{
    bucket = "{bucket}"
    prefix = "{prefix}"
  }}
}}
'''
        with open(os.path.join(work_dir, "backend.tf"), "w") as f:
            f.write(backend_content)

        # Write provider.tf if not present
        if "provider.tf" not in tf_files:
            provider_content = f'''terraform {{
  required_version = ">= 1.5.0"
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

provider "google" {{
  project = "{project_id}"
}}
'''
            with open(os.path.join(work_dir, "provider.tf"), "w") as f:
                f.write(provider_content)

        # Step 1: terraform init
        job["progress"]["message"] = "Running terraform init..."
        stdout, stderr, rc = _run_terraform(["init", "-no-color"], work_dir, timeout=180)
        if rc != 0:
            job["status"] = "failed"
            job["error"] = f"terraform init failed: {stderr}"
            return

        # Step 2: Initial plan
        job["progress"]["message"] = "Running initial terraform plan..."
        stdout, stderr, rc = _run_terraform(["plan", "-no-color", "-lock=false"], work_dir)
        drift_result = _parse_plan_output(stdout, stderr)

        if not drift_result.has_drift:
            job["status"] = "completed"
            job["result"] = {
                "drift_detected": False,
                "message": "No changes. Your infrastructure matches the configuration.",
                "iterations_needed": 0,
                "final_files": _read_tf_files(work_dir),
            }
            return

        # Step 3: Iterative fix loop
        for iteration in range(1, MAX_FIX_ITERATIONS + 1):
            job["progress"]["iteration"] = iteration
            job["progress"]["message"] = f"Fixing drift (attempt {iteration}/{MAX_FIX_ITERATIONS})..."

            job["fix_history"].append({
                "iteration": iteration,
                "drift": {
                    "changed": drift_result.resources_changed,
                    "added": drift_result.resources_added,
                    "destroyed": drift_result.resources_destroyed,
                },
            })

            # Get all resource .tf files (skip provider.tf, backend.tf, import.tf)
            resource_files = {
                f: open(os.path.join(work_dir, f)).read()
                for f in os.listdir(work_dir)
                if f.endswith(".tf") and f not in ("provider.tf", "backend.tf", "import.tf")
            }

            # Concatenate all resource content for AI
            all_tf_content = "\n\n".join(
                f"# --- {fname} ---\n{content}" for fname, content in resource_files.items()
            )

            # Call AI to fix
            prompt = FIX_DRIFT_PROMPT.format(
                tf_content=all_tf_content,
                plan_output=drift_result.plan_output[-4000:],  # Limit plan output size
            )

            try:
                from app.services.ai_cleaner import call_ai
                fixed_content = await call_ai(
                    prompt=prompt,
                    provider=ai_config.provider,
                    api_key=ai_config.api_key,
                    model=ai_config.model or None,
                    endpoint_url=ai_config.endpoint_url or None,
                )
            except Exception as e:
                logger.error(f"AI fix attempt {iteration} failed: {e}")
                if iteration == MAX_FIX_ITERATIONS:
                    job["status"] = "failed"
                    job["error"] = f"AI fix failed after {iteration} attempts: {str(e)}"
                    return
                continue

            # Write fixed content back
            # If AI returns a single block, write to main.tf; otherwise split by markers
            if "# ---" in fixed_content:
                # AI preserved file markers, split back
                current_file = None
                current_lines = []
                for line in fixed_content.split("\n"):
                    marker_match = re.match(r"# --- (.+\.tf) ---", line)
                    if marker_match:
                        if current_file and current_lines:
                            with open(os.path.join(work_dir, current_file), "w") as f:
                                f.write("\n".join(current_lines))
                        current_file = marker_match.group(1)
                        current_lines = []
                    else:
                        current_lines.append(line)
                if current_file and current_lines:
                    with open(os.path.join(work_dir, current_file), "w") as f:
                        f.write("\n".join(current_lines))
            else:
                # Write all to first resource file
                first_file = next(iter(resource_files.keys()), "main.tf")
                with open(os.path.join(work_dir, first_file), "w") as f:
                    f.write(fixed_content)

            # Re-run plan
            job["progress"]["message"] = f"Verifying fix (attempt {iteration}/{MAX_FIX_ITERATIONS})..."
            stdout, stderr, rc = _run_terraform(["plan", "-no-color", "-lock=false"], work_dir)
            drift_result = _parse_plan_output(stdout, stderr)

            if not drift_result.has_drift:
                # Success!
                job["status"] = "completed"
                job["result"] = {
                    "drift_detected": True,
                    "drift_fixed": True,
                    "message": f"Drift fixed successfully after {iteration} iteration(s).",
                    "iterations_needed": iteration,
                    "final_files": _read_tf_files(work_dir),
                }
                return

        # Exhausted retries
        job["status"] = "completed"
        job["result"] = {
            "drift_detected": True,
            "drift_fixed": False,
            "message": f"Could not fully resolve drift after {MAX_FIX_ITERATIONS} attempts. Manual review needed.",
            "iterations_needed": MAX_FIX_ITERATIONS,
            "remaining_drift": drift_result.plan_output[-2000:],
            "final_files": _read_tf_files(work_dir),
        }

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        logger.error(f"Drift detection job {job_id} failed: {e}")
    finally:
        # Cleanup temp directory
        shutil.rmtree(work_dir, ignore_errors=True)


def _read_tf_files(work_dir: str) -> dict[str, str]:
    """Read all .tf files from work directory."""
    files = {}
    for f in os.listdir(work_dir):
        if f.endswith(".tf"):
            with open(os.path.join(work_dir, f)) as fh:
                files[f] = fh.read()
    return files
