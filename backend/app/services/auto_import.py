"""Auto Import service.

Allows users to upload their own .tf files, automatically generates import.tf
using AI (based on Terraform provider documentation), executes the import,
and reports drift for user decision.

Flow:
1. Validate uploaded files (backend.tf required)
2. terraform init
3. terraform plan (detect errors)
4. AI fix errors if any
5. AI generates import.tf from plan output (knows resource import ID formats)
6. terraform apply (execute imports)
7. terraform plan (detect drift)
8. Report drift to user for decision
"""

import asyncio
import os
import re
import shutil
import tempfile
import time
import uuid
from typing import Any

from app.core.logging import get_logger
from app.services.ai_settings import get_active_config
from app.services.drift import (
    _strip_markdown_fences,
    _sanitize_line,
    _detect_fatal_error,
    _read_tf_files,
    _write_fixed_content,
)

logger = get_logger("auto_import")

# In-memory job storage
_auto_import_jobs: dict[str, dict[str, Any]] = {}

# Pub/sub for real-time log streaming
_auto_import_subscribers: dict[str, list[asyncio.Queue]] = {}

MAX_FIX_ITERATIONS = 5
MAX_SUBSCRIBERS_PER_JOB = 5
MAX_QUEUE_SIZE = 1000

GENERATE_IMPORT_PROMPT = """You are an expert Terraform engineer. Your task is to generate import blocks
for resources defined in the Terraform code.

CONTEXT:
- The user has Terraform .tf files that define existing infrastructure.
- The resources already exist in the cloud but are NOT in the Terraform state yet.
- You must generate `import {{ }}` blocks (Terraform 1.5+ syntax) for each resource.
- The import ID format depends on the resource type and provider.

TERRAFORM IMPORT ID FORMATS (Google Provider):
- google_compute_instance: "projects/{{project}}/zones/{{zone}}/instances/{{name}}"
- google_compute_network: "projects/{{project}}/global/networks/{{name}}"
- google_compute_subnetwork: "projects/{{project}}/regions/{{region}}/subnetworks/{{name}}"
- google_compute_firewall: "projects/{{project}}/global/firewalls/{{name}}"
- google_compute_address: "projects/{{project}}/regions/{{region}}/addresses/{{name}}"
- google_compute_global_address: "projects/{{project}}/global/addresses/{{name}}"
- google_compute_disk: "projects/{{project}}/zones/{{zone}}/disks/{{name}}"
- google_compute_router: "projects/{{project}}/regions/{{region}}/routers/{{name}}"
- google_compute_route: "projects/{{project}}/global/routes/{{name}}"
- google_compute_health_check: "projects/{{project}}/global/healthChecks/{{name}}"
- google_compute_region_health_check: "projects/{{project}}/regions/{{region}}/healthChecks/{{name}}"
- google_compute_backend_service: "projects/{{project}}/global/backendServices/{{name}}"
- google_compute_region_backend_service: "projects/{{project}}/regions/{{region}}/backendServices/{{name}}"
- google_compute_url_map: "projects/{{project}}/global/urlMaps/{{name}}"
- google_compute_target_http_proxy: "projects/{{project}}/global/targetHttpProxies/{{name}}"
- google_compute_target_https_proxy: "projects/{{project}}/global/targetHttpsProxies/{{name}}"
- google_compute_global_forwarding_rule: "projects/{{project}}/global/forwardingRules/{{name}}"
- google_compute_forwarding_rule: "projects/{{project}}/regions/{{region}}/forwardingRules/{{name}}"
- google_compute_instance_template: "projects/{{project}}/global/instanceTemplates/{{name}}"
- google_compute_instance_group_manager: "projects/{{project}}/zones/{{zone}}/instanceGroupManagers/{{name}}"
- google_compute_region_instance_group_manager: "projects/{{project}}/regions/{{region}}/instanceGroupManagers/{{name}}"
- google_compute_security_policy: "projects/{{project}}/global/securityPolicies/{{name}}"
- google_compute_region_security_policy: "projects/{{project}}/regions/{{region}}/securityPolicies/{{name}}"
- google_compute_ssl_certificate: "projects/{{project}}/global/sslCertificates/{{name}}"
- google_compute_ssl_policy: "projects/{{project}}/global/sslPolicies/{{name}}"
- google_compute_snapshot: "projects/{{project}}/global/snapshots/{{name}}"
- google_compute_image: "projects/{{project}}/global/images/{{name}}"
- google_compute_reservation: "projects/{{project}}/zones/{{zone}}/reservations/{{name}}"
- google_compute_vpn_gateway: "projects/{{project}}/regions/{{region}}/vpnGateways/{{name}}"
- google_compute_vpn_tunnel: "projects/{{project}}/regions/{{region}}/vpnTunnels/{{name}}"
- google_compute_router_nat: "projects/{{project}}/regions/{{region}}/routers/{{router}}/{{name}}"
- google_storage_bucket: "projects/{{project}}/buckets/{{name}}" OR just "{{name}}"
- google_sql_database_instance: "projects/{{project}}/instances/{{name}}"
- google_container_cluster: "projects/{{project}}/locations/{{location}}/clusters/{{name}}"
- google_container_node_pool: "projects/{{project}}/locations/{{location}}/clusters/{{cluster}}/nodePools/{{name}}"
- google_cloud_run_service: "locations/{{location}}/namespaces/{{project}}/services/{{name}}"
- google_cloud_run_v2_service: "projects/{{project}}/locations/{{location}}/services/{{name}}"
- google_cloudfunctions_function: "projects/{{project}}/locations/{{region}}/functions/{{name}}"
- google_cloudfunctions2_function: "projects/{{project}}/locations/{{region}}/functions/{{name}}"
- google_pubsub_topic: "projects/{{project}}/topics/{{name}}"
- google_pubsub_subscription: "projects/{{project}}/subscriptions/{{name}}"
- google_redis_instance: "projects/{{project}}/locations/{{region}}/instances/{{name}}"
- google_dns_managed_zone: "projects/{{project}}/managedZones/{{name}}"
- google_dns_policy: "projects/{{project}}/policies/{{name}}"
- google_bigquery_dataset: "projects/{{project}}/datasets/{{dataset_id}}"
- google_secret_manager_secret: "projects/{{project}}/secrets/{{secret_id}}"
- google_kms_key_ring: "projects/{{project}}/locations/{{location}}/keyRings/{{name}}"
- google_kms_crypto_key: "projects/{{project}}/locations/{{location}}/keyRings/{{key_ring}}/cryptoKeys/{{name}}"
- google_artifact_registry_repository: "projects/{{project}}/locations/{{location}}/repositories/{{name}}"
- google_cloud_scheduler_job: "projects/{{project}}/locations/{{location}}/jobs/{{name}}"
- google_cloud_tasks_queue: "projects/{{project}}/locations/{{location}}/queues/{{name}}"
- google_service_account: "projects/{{project}}/serviceAccounts/{{email}}"
- google_project_iam_member: "{{project}} {{role}} {{member}}"
- google_project_iam_binding: "{{project}} {{role}}"
- google_logging_project_sink: "projects/{{project}}/sinks/{{name}}"
- google_monitoring_alert_policy: "projects/{{project}}/alertPolicies/{{name}}"
- google_filestore_instance: "projects/{{project}}/locations/{{location}}/instances/{{name}}"
- google_spanner_instance: "projects/{{project}}/instances/{{name}}"
- google_dataflow_job: "projects/{{project}}/locations/{{location}}/jobs/{{job_id}}"
- google_composer_environment: "projects/{{project}}/locations/{{region}}/environments/{{name}}"
- google_vpc_access_connector: "projects/{{project}}/locations/{{region}}/connectors/{{name}}"
- google_compute_managed_ssl_certificate: "projects/{{project}}/global/sslCertificates/{{name}}"
- google_project: "projects/{{project_id}}"
- google_folder: "folders/{{folder_id}}"

TERRAFORM IMPORT ID FORMATS (AWS Provider):
- aws_instance: "i-xxxxxxxxx"
- aws_vpc: "vpc-xxxxxxxxx"
- aws_subnet: "subnet-xxxxxxxxx"
- aws_security_group: "sg-xxxxxxxxx"
- aws_s3_bucket: "bucket-name"
- aws_iam_role: "role-name"
- aws_lambda_function: "function-name"
- aws_dynamodb_table: "table-name"
- aws_rds_cluster: "cluster-identifier"
- aws_eks_cluster: "cluster-name"
- aws_ecs_cluster: "arn:aws:ecs:region:account:cluster/name"
- aws_route53_zone: "zone-id"
- aws_cloudfront_distribution: "distribution-id"
- aws_sqs_queue: "queue-url"
- aws_sns_topic: "arn:aws:sns:region:account:topic-name"
- aws_elasticache_cluster: "cluster-id"
- aws_lb: "arn:aws:elasticloadbalancing:region:account:loadbalancer/type/name/id"

RULES:
- Generate one `import {{ }}` block per resource defined in the .tf code.
- Extract the project, region, zone, name from the resource attributes in the code.
- If a field is not explicit in the resource, check for a provider-level default.
- Use the exact resource address: type.name (e.g., google_compute_instance.my_vm)
- Return ONLY the import blocks, nothing else.
- Do NOT include any resource/data/provider blocks.
- Do NOT wrap in markdown fences.

EXAMPLE OUTPUT:
import {{
  to = google_compute_instance.web_server
  id = "projects/my-project/zones/us-central1-a/instances/web-server"
}}

import {{
  to = google_storage_bucket.data
  id = "my-project-data-bucket"
}}

Terraform Code:
```hcl
{tf_content}
```

Terraform Plan Output (resources to import):
```
{plan_output}
```

Generate the import blocks for ALL resources shown in the plan as "will be created" (+ create).
These resources already exist — they need to be imported, not created."""


# ---------------------------------------------------------------------------
# Pub/Sub for real-time log streaming
# ---------------------------------------------------------------------------


def subscribe(job_id: str) -> asyncio.Queue:
    """Subscribe to log events for an auto-import job."""
    if job_id not in _auto_import_subscribers:
        _auto_import_subscribers[job_id] = []
    if len(_auto_import_subscribers[job_id]) >= MAX_SUBSCRIBERS_PER_JOB:
        raise RuntimeError(f"Max subscribers ({MAX_SUBSCRIBERS_PER_JOB}) reached for job {job_id}")
    queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    _auto_import_subscribers[job_id].append(queue)
    return queue


def unsubscribe(job_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from log events."""
    if job_id in _auto_import_subscribers:
        try:
            _auto_import_subscribers[job_id].remove(queue)
        except ValueError:
            pass
        if not _auto_import_subscribers[job_id]:
            del _auto_import_subscribers[job_id]


def _emit(job_id: str, message: dict) -> None:
    """Emit a message to all subscribers (non-blocking)."""
    for queue in _auto_import_subscribers.get(job_id, []):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
                queue.put_nowait(message)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass


def _emit_log(job_id: str, line: str, stream: str, phase: str) -> None:
    _emit(job_id, {"type": "log", "data": {"line": line, "stream": stream, "phase": phase, "timestamp": time.time()}})


def _emit_phase(job_id: str, phase: str, message: str) -> None:
    _emit(job_id, {"type": "phase", "data": {"phase": phase, "message": message, "timestamp": time.time()}})


def _emit_complete(job_id: str, status: str, message: str) -> None:
    _emit(job_id, {"type": "complete", "data": {"status": status, "message": message, "timestamp": time.time()}})


def _emit_drift_decision(job_id: str, drift_summary: dict) -> None:
    """Emit a special message asking the user what to do about drift."""
    _emit(job_id, {"type": "drift_decision", "data": {"drift": drift_summary, "timestamp": time.time()}})


# ---------------------------------------------------------------------------
# Terraform execution (local version using auto_import pub/sub)
# ---------------------------------------------------------------------------


async def _run_terraform_streaming(
    args: list[str],
    cwd: str,
    job_id: str,
    phase: str,
    timeout: int = 120,
) -> tuple[str, str, int]:
    """Run terraform with real-time streaming to auto_import subscribers."""
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    try:
        process = await asyncio.create_subprocess_exec(
            "terraform",
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def read_stream(stream: asyncio.StreamReader, stream_name: str, buffer: list[str]):
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").rstrip("\n")
                sanitized = _sanitize_line(line, cwd)
                buffer.append(sanitized)
                _emit_log(job_id, sanitized, stream_name, phase)

        await asyncio.wait_for(
            asyncio.gather(
                read_stream(process.stdout, "stdout", stdout_lines),
                read_stream(process.stderr, "stderr", stderr_lines),
            ),
            timeout=timeout,
        )

        await process.wait()
        returncode = process.returncode

    except asyncio.TimeoutError:
        try:
            process.kill()
            await process.wait()
        except ProcessLookupError:
            pass
        _emit_log(job_id, f"[ERROR] Command timed out after {timeout}s", "stderr", phase)
        stderr_lines.append(f"Command timed out after {timeout}s")
        returncode = -1

    except Exception as e:
        _emit_log(job_id, f"[ERROR] {str(e)}", "stderr", phase)
        stderr_lines.append(str(e))
        returncode = -1

    # Strip ANSI for parsing (not for streaming)
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    stdout = ansi_escape.sub("", "\n".join(stdout_lines))
    stderr = ansi_escape.sub("", "\n".join(stderr_lines))

    return stdout, stderr, returncode


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------


def get_auto_import_job(job_id: str) -> dict | None:
    return _auto_import_jobs.get(job_id)


def cancel_auto_import_job(job_id: str) -> bool:
    job = _auto_import_jobs.get(job_id)
    if not job or job["status"] != "running":
        return False
    job["cancel_requested"] = True
    return True


def set_drift_decision(job_id: str, decision: str) -> bool:
    """Set the user's decision about drift: 'fix', 'download', 'ignore'."""
    job = _auto_import_jobs.get(job_id)
    if not job or job.get("awaiting_decision") is not True:
        return False
    job["drift_decision"] = decision
    return True


async def start_auto_import(tf_files: dict[str, str]) -> str:
    """Start an auto-import job.

    Args:
        tf_files: Dict of filename → HCL content. Must include backend.tf.

    Returns:
        Job ID for tracking.
    """
    job_id = str(uuid.uuid4())
    _auto_import_jobs[job_id] = {
        "status": "running",
        "phase": "init",
        "progress": {"message": "Starting..."},
        "started_at": time.time(),
        "result": None,
        "error": None,
        "awaiting_decision": False,
        "drift_decision": None,
        "cancel_requested": False,
    }

    asyncio.create_task(_run_auto_import(job_id, tf_files))
    return job_id


async def _run_auto_import(job_id: str, tf_files: dict[str, str]) -> None:
    """Execute the auto-import flow."""
    job = _auto_import_jobs[job_id]

    ai_config = get_active_config()
    if not ai_config:
        job["status"] = "failed"
        job["error"] = "No AI provider configured. Configure one in Settings."
        _emit_complete(job_id, "failed", "No AI provider configured.")
        return

    work_dir = tempfile.mkdtemp(prefix="terramorph-autoimport-")

    try:
        # Write all user files
        for filename, content in tf_files.items():
            filepath = os.path.join(work_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)

        # --- Step 1: terraform init ---
        job["phase"] = "init"
        job["progress"]["message"] = "Running terraform init..."
        _emit_phase(job_id, "init", "Running terraform init...")

        stdout, stderr, rc = await _run_terraform_streaming(
            ["init", "-no-color"], work_dir, job_id, "init", timeout=180
        )
        if rc != 0:
            job["status"] = "failed"
            job["error"] = f"terraform init failed: {stderr}"
            _emit_complete(job_id, "failed", "terraform init failed")
            return

        if job.get("cancel_requested"):
            job["status"] = "cancelled"
            _emit_complete(job_id, "cancelled", "Cancelled by user.")
            return

        # --- Step 2: terraform plan ---
        job["phase"] = "plan"
        job["progress"]["message"] = "Running terraform plan..."
        _emit_phase(job_id, "plan", "Running terraform plan...")

        stdout, stderr, rc = await _run_terraform_streaming(
            ["plan", "-no-color", "-lock=false"], work_dir, job_id, "plan"
        )

        # Check for fatal errors
        combined = stdout + "\n" + stderr
        fatal = _detect_fatal_error(combined, rc)
        if fatal:
            job["status"] = "failed"
            job["error"] = fatal
            _emit_complete(job_id, "failed", fatal)
            return

        # --- Step 2b: AI fix HCL errors if plan failed ---
        if rc != 0:
            _emit_log(job_id, "▶ Plan has errors, attempting AI fix...", "stdout", "fix")
            for attempt in range(1, MAX_FIX_ITERATIONS + 1):
                if job.get("cancel_requested"):
                    job["status"] = "cancelled"
                    _emit_complete(job_id, "cancelled", "Cancelled by user.")
                    return

                job["phase"] = "fix"
                _emit_phase(job_id, "fix", f"AI fixing errors (attempt {attempt}/{MAX_FIX_ITERATIONS})...")

                resource_files = {
                    f: open(os.path.join(work_dir, f)).read()
                    for f in os.listdir(work_dir)
                    if f.endswith(".tf") and f not in ("backend.tf", "import.tf")
                }
                all_tf = "\n\n".join(f"# --- {fn} ---\n{c}" for fn, c in resource_files.items())

                from app.services.drift import FIX_DRIFT_PROMPT
                prompt = FIX_DRIFT_PROMPT.format(tf_content=all_tf, plan_output=(stdout + "\n" + stderr)[-4000:])
                _emit_log(job_id, "▶ Sending to AI...", "stdout", "fix")

                try:
                    from app.services.ai_cleaner import call_ai
                    fixed = await call_ai(prompt=prompt, provider=ai_config.provider, api_key=ai_config.api_key, model=ai_config.model or None, endpoint_url=ai_config.endpoint_url or None)
                except Exception as e:
                    _emit_log(job_id, f"[ERROR] AI failed: {e}", "stderr", "fix")
                    if attempt == MAX_FIX_ITERATIONS:
                        job["status"] = "failed"
                        job["error"] = f"AI could not fix errors: {e}"
                        _emit_complete(job_id, "failed", job["error"])
                        return
                    continue

                if not fixed or not fixed.strip():
                    continue
                fixed = _strip_markdown_fences(fixed)
                if not re.search(r'\b(resource|data|module|variable|output|locals)\s+"', fixed):
                    continue

                _emit_log(job_id, f"✓ Applying fix ({len(fixed)} chars)...", "stdout", "fix")
                _write_fixed_content(work_dir, fixed, resource_files)

                stdout, stderr, rc = await _run_terraform_streaming(
                    ["plan", "-no-color", "-lock=false"], work_dir, job_id, "plan"
                )
                if rc == 0:
                    _emit_log(job_id, "✓ Errors resolved!", "stdout", "fix")
                    break
                fatal = _detect_fatal_error(stdout + "\n" + stderr, rc)
                if fatal:
                    job["status"] = "failed"
                    job["error"] = fatal
                    _emit_complete(job_id, "failed", fatal)
                    return
            else:
                job["status"] = "failed"
                job["error"] = "Could not fix errors after max attempts."
                _emit_complete(job_id, "failed", job["error"])
                return

        if job.get("cancel_requested"):
            job["status"] = "cancelled"
            _emit_complete(job_id, "cancelled", "Cancelled by user.")
            return

        # --- Step 3: Generate import.tf using AI ---
        # Check if plan shows resources to create (need importing)
        plan_output = stdout + "\n" + stderr
        resources_to_add = re.findall(r"# (.+) will be created", plan_output)

        if not resources_to_add:
            job["status"] = "completed"
            job["phase"] = "done"
            job["result"] = {"message": "No resources to import. All resources are already in state.", "final_files": _read_tf_files(work_dir)}
            _emit_log(job_id, "✓ No resources need importing.", "stdout", "plan")
            _emit_complete(job_id, "completed", "No resources to import.")
            return

        job["phase"] = "import"
        _emit_phase(job_id, "import", f"Generating import blocks for {len(resources_to_add)} resource(s)...")
        _emit_log(job_id, f"▶ Found {len(resources_to_add)} resource(s) to import. Generating import.tf with AI...", "stdout", "import")

        # Get resource code for AI context
        resource_files = {
            f: open(os.path.join(work_dir, f)).read()
            for f in os.listdir(work_dir)
            if f.endswith(".tf") and f not in ("backend.tf", "import.tf")
        }
        all_tf = "\n\n".join(f"# --- {fn} ---\n{c}" for fn, c in resource_files.items())

        import_prompt = GENERATE_IMPORT_PROMPT.format(tf_content=all_tf, plan_output=plan_output[-6000:])

        try:
            from app.services.ai_cleaner import call_ai
            import_content = await call_ai(prompt=import_prompt, provider=ai_config.provider, api_key=ai_config.api_key, model=ai_config.model or None, endpoint_url=ai_config.endpoint_url or None)
        except Exception as e:
            job["status"] = "failed"
            job["error"] = f"AI failed to generate import blocks: {e}"
            _emit_complete(job_id, "failed", job["error"])
            return

        if not import_content or not import_content.strip():
            job["status"] = "failed"
            job["error"] = "AI returned empty import blocks."
            _emit_complete(job_id, "failed", job["error"])
            return

        import_content = _strip_markdown_fences(import_content)

        # Validate it looks like import blocks
        if "import {" not in import_content and "import{" not in import_content:
            _emit_log(job_id, "[WARN] AI response doesn't contain import blocks, retrying...", "stderr", "import")
            job["status"] = "failed"
            job["error"] = "AI did not generate valid import blocks."
            _emit_complete(job_id, "failed", job["error"])
            return

        # Write import.tf
        with open(os.path.join(work_dir, "import.tf"), "w") as f:
            f.write(import_content)
        _emit_log(job_id, f"✓ Generated import.tf ({len(resources_to_add)} imports)", "stdout", "import")

        if job.get("cancel_requested"):
            job["status"] = "cancelled"
            _emit_complete(job_id, "cancelled", "Cancelled by user.")
            return

        # --- Step 4: terraform apply (execute imports) ---
        _emit_phase(job_id, "import", "Executing terraform apply (importing resources)...")
        _emit_log(job_id, "▶ Running terraform apply to import resources...", "stdout", "import")

        stdout, stderr, rc = await _run_terraform_streaming(
            ["apply", "-auto-approve", "-no-color", "-lock=false"], work_dir, job_id, "import", timeout=300
        )

        if rc != 0:
            apply_output = stdout + "\n" + stderr
            if "Resource already managed" in apply_output:
                _emit_log(job_id, "✓ Some resources already in state.", "stdout", "import")
            elif "Cannot import non-existent" in apply_output:
                _emit_log(job_id, "[WARN] Some resources not found remotely.", "stderr", "import")
            else:
                _emit_log(job_id, f"[WARN] Apply had issues (rc={rc}), continuing...", "stderr", "import")

        # Remove import.tf after apply
        import_path = os.path.join(work_dir, "import.tf")
        if os.path.exists(import_path):
            os.remove(import_path)

        if job.get("cancel_requested"):
            job["status"] = "cancelled"
            _emit_complete(job_id, "cancelled", "Cancelled by user.")
            return

        # --- Step 5: Final plan to check drift ---
        job["phase"] = "verify"
        _emit_phase(job_id, "verify", "Running final plan to check for drift...")

        stdout, stderr, rc = await _run_terraform_streaming(
            ["plan", "-no-color", "-lock=false"], work_dir, job_id, "verify"
        )

        plan_output = stdout + "\n" + stderr
        plan_summary = re.search(r"Plan:\s*(\d+)\s*to add,\s*(\d+)\s*to change,\s*(\d+)\s*to destroy", plan_output)
        no_changes = "No changes" in plan_output

        if no_changes:
            job["status"] = "completed"
            job["phase"] = "done"
            job["result"] = {"message": "Import successful! No drift detected.", "drift": False, "final_files": _read_tf_files(work_dir)}
            _emit_log(job_id, "✓ Import complete. No drift — infrastructure matches code.", "stdout", "verify")
            _emit_complete(job_id, "completed", "Import successful! No drift.")
            return

        # Drift detected — ask user what to do
        summary_add = int(plan_summary.group(1)) if plan_summary else 0
        summary_change = int(plan_summary.group(2)) if plan_summary else 0
        summary_destroy = int(plan_summary.group(3)) if plan_summary else 0

        drift_info = {
            "added": summary_add,
            "changed": summary_change,
            "destroyed": summary_destroy,
            "plan_output": plan_output[-3000:],
        }

        job["awaiting_decision"] = True
        job["phase"] = "decision"
        job["progress"]["message"] = "Drift detected — awaiting user decision..."
        _emit_log(job_id, f"⚠ Drift detected: {summary_add} to add, {summary_change} to change, {summary_destroy} to destroy", "stderr", "verify")
        _emit_drift_decision(job_id, drift_info)

        # Wait for user decision (poll every 2s, timeout 5 min)
        for _ in range(150):
            await asyncio.sleep(2)
            if job.get("cancel_requested"):
                job["status"] = "cancelled"
                _emit_complete(job_id, "cancelled", "Cancelled by user.")
                return
            if job.get("drift_decision"):
                break
        else:
            job["status"] = "completed"
            job["result"] = {"message": "Timeout waiting for drift decision.", "drift": True, "drift_info": drift_info, "final_files": _read_tf_files(work_dir)}
            _emit_complete(job_id, "completed", "Timeout — drift not resolved.")
            return

        decision = job["drift_decision"]
        job["awaiting_decision"] = False

        if decision == "fix":
            # AI drift fix loop (reuse drift logic)
            _emit_phase(job_id, "fix", "AI fixing drift...")
            from app.services.drift import FIX_DRIFT_PROMPT, _parse_plan_output

            drift_result = _parse_plan_output(stdout, stderr)
            for iteration in range(1, MAX_FIX_ITERATIONS + 1):
                if job.get("cancel_requested"):
                    job["status"] = "cancelled"
                    _emit_complete(job_id, "cancelled", "Cancelled by user.")
                    return

                _emit_phase(job_id, "fix", f"AI fixing drift (attempt {iteration}/{MAX_FIX_ITERATIONS})...")
                resource_files = {
                    f: open(os.path.join(work_dir, f)).read()
                    for f in os.listdir(work_dir)
                    if f.endswith(".tf") and f not in ("backend.tf", "import.tf")
                }
                all_tf = "\n\n".join(f"# --- {fn} ---\n{c}" for fn, c in resource_files.items())
                prompt = FIX_DRIFT_PROMPT.format(tf_content=all_tf, plan_output=drift_result.plan_output[-4000:])
                _emit_log(job_id, f"▶ AI fixing drift (attempt {iteration})...", "stdout", "fix")

                try:
                    from app.services.ai_cleaner import call_ai
                    fixed = await call_ai(prompt=prompt, provider=ai_config.provider, api_key=ai_config.api_key, model=ai_config.model or None, endpoint_url=ai_config.endpoint_url or None)
                except Exception as e:
                    _emit_log(job_id, f"[ERROR] {e}", "stderr", "fix")
                    continue

                if not fixed or not fixed.strip():
                    continue
                fixed = _strip_markdown_fences(fixed)
                if not re.search(r'\b(resource|data|module|variable|output|locals)\s+"', fixed):
                    continue

                _write_fixed_content(work_dir, fixed, resource_files)
                stdout, stderr, rc = await _run_terraform_streaming(
                    ["plan", "-no-color", "-lock=false"], work_dir, job_id, "verify"
                )
                drift_result = _parse_plan_output(stdout, stderr)
                if not drift_result.has_drift:
                    job["status"] = "completed"
                    job["phase"] = "done"
                    job["result"] = {"message": f"Import + drift fix complete ({iteration} iterations).", "drift": False, "final_files": _read_tf_files(work_dir)}
                    _emit_complete(job_id, "completed", f"Drift fixed after {iteration} iteration(s)!")
                    return

            job["status"] = "completed"
            job["result"] = {"message": "Import done but drift not fully resolved.", "drift": True, "drift_info": drift_info, "final_files": _read_tf_files(work_dir)}
            _emit_complete(job_id, "completed", "Drift not fully resolved.")

        elif decision == "download":
            job["status"] = "completed"
            job["phase"] = "done"
            job["result"] = {"message": "Import complete. Drift plan available for download.", "drift": True, "drift_info": drift_info, "final_files": _read_tf_files(work_dir)}
            _emit_complete(job_id, "completed", "Import done. Plan available.")

        else:  # ignore
            job["status"] = "completed"
            job["phase"] = "done"
            job["result"] = {"message": "Import complete. Drift ignored.", "drift": True, "drift_info": drift_info, "final_files": _read_tf_files(work_dir)}
            _emit_complete(job_id, "completed", "Import done. Drift ignored.")

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        logger.error(f"Auto-import job {job_id} failed: {e}")
        _emit_complete(job_id, "failed", str(e))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        await asyncio.sleep(2)
        if job_id in _auto_import_subscribers:
            del _auto_import_subscribers[job_id]
