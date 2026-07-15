"""Generation request/response models."""

from enum import Enum

from pydantic import BaseModel, Field


class OutputFormat(str, Enum):
    """Output format for generated Terraform files."""

    SINGLE_FILE = "single_file"
    PER_RESOURCE_TYPE = "per_resource_type"


class GenerationStyle(str, Enum):
    """Code generation style."""

    FLAT = "flat"
    MODULE = "module"


class BackendStateConfig(BaseModel):
    """GCS backend state configuration."""

    bucket: str = Field(description="GCS bucket name for storing tfstate")
    prefix: str = Field(
        default="terraform/state",
        description="Path prefix within the bucket (e.g., terraform/state/pro)",
    )


class GenerationOptions(BaseModel):
    """Options for Terraform generation."""

    include_provider_block: bool = True
    include_import_script: bool = True
    output_format: OutputFormat = OutputFormat.PER_RESOURCE_TYPE
    generation_style: GenerationStyle = GenerationStyle.FLAT
    backend_state: BackendStateConfig | None = Field(
        default=None,
        description="GCS backend configuration. If provided, generates backend.tf",
    )


class GenerationRequest(BaseModel):
    """Request to generate Terraform code."""

    job_id: str = Field(description="Discovery job ID to generate from")
    resource_ids: list[str] = Field(
        default=["all"],
        description="Resource IDs to generate, or ['all'] for all discovered resources",
    )
    options: GenerationOptions = Field(default_factory=GenerationOptions)


class GeneratedFile(BaseModel):
    """A generated Terraform file."""

    filename: str
    content: str


class GenerationResult(BaseModel):
    """Result of Terraform code generation."""

    files: list[GeneratedFile] = Field(default_factory=list)
    total_resources: int = 0
    import_commands: int = 0
