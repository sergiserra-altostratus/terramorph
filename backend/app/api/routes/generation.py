"""Terraform code generation endpoints."""

import io
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.discovery.orchestrator import get_job_results
from app.generation.fmt import fmt_content
from app.generation.hcl_renderer import HCLRenderer
from app.generation.import_generator import ImportGenerator
from app.models.generation import (
    GeneratedFile,
    GenerationRequest,
    GenerationResult,
    GenerationStyle,
    OutputFormat,
)

router = APIRouter()

_renderer = HCLRenderer()
_import_gen = ImportGenerator()


@router.post("/generate/terraform", response_model=GenerationResult)
async def generate_terraform(request: GenerationRequest) -> GenerationResult:
    """Generate Terraform HCL code from discovered resources."""
    from app.services.stats import track_generation

    result = get_job_results(request.job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{request.job_id}' not found")

    if not result.resources:
        raise HTTPException(status_code=400, detail="No resources found in this job")

    # Filter resources if specific IDs provided
    if request.resource_ids != ["all"]:
        resources = [r for r in result.resources if r.id in request.resource_ids]
    else:
        resources = result.resources

    files: list[GeneratedFile] = []

    # Generate provider.tf
    if request.options.include_provider_block:
        projects = list({r.project for r in resources})
        provider_content = _renderer.render_provider(projects[0] if projects else "")
        files.append(GeneratedFile(filename="provider.tf", content=provider_content))

    # Generate backend.tf if state config provided
    if request.options.backend_state:
        backend_content = _renderer.render_backend(
            bucket=request.options.backend_state.bucket,
            prefix=request.options.backend_state.prefix,
        )
        files.append(GeneratedFile(filename="backend.tf", content=backend_content))

    # Generate resource files
    use_modules = request.options.generation_style == GenerationStyle.MODULE
    if request.options.output_format == OutputFormat.SINGLE_FILE:
        if use_modules:
            content = _renderer.render_all_as_modules(resources)
        else:
            content = _renderer.render_all(resources)
        files.append(GeneratedFile(filename="main.tf", content=content))
    else:
        if use_modules:
            resource_files = _renderer.render_by_type_as_modules(resources)
        else:
            resource_files = _renderer.render_by_type(resources)
        for filename, content in resource_files.items():
            files.append(GeneratedFile(filename=filename, content=content))

    # Generate import blocks (.tf format - Terraform 1.5+)
    if request.options.include_import_script:
        import_content = _import_gen.generate(resources)
        files.append(GeneratedFile(filename="import.tf", content=import_content))

    # Track usage statistics
    track_generation(resources)

    # Apply terraform fmt to all .tf files
    formatted_files = []
    for f in files:
        if f.filename.endswith(".tf"):
            formatted_files.append(GeneratedFile(filename=f.filename, content=fmt_content(f.content)))
        else:
            formatted_files.append(f)

    return GenerationResult(
        files=formatted_files,
        total_resources=len(resources),
        import_commands=len(resources),
    )


@router.get("/generate/download/{job_id}")
async def download_terraform(job_id: str) -> StreamingResponse:
    """Download generated Terraform files as a ZIP archive."""
    result = get_job_results(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if not result.resources:
        raise HTTPException(status_code=400, detail="No resources found in this job")

    resources = result.resources
    projects = list({r.project for r in resources})

    # Generate all files
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Provider
        provider_content = fmt_content(_renderer.render_provider(projects[0] if projects else ""))
        zf.writestr("terraform/provider.tf", provider_content)

        # Backend state (default: no backend.tf in download unless specified via POST)

        # Resources by type
        resource_files = _renderer.render_by_type(resources)
        for filename, content in resource_files.items():
            zf.writestr(f"terraform/{filename}", fmt_content(content))

        # Import blocks (.tf format)
        import_content = fmt_content(_import_gen.generate(resources))
        zf.writestr("terraform/import.tf", import_content)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=terramorph-{job_id[:8]}.zip"},
    )
