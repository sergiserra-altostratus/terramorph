"""Input validation for user-controlled values passed to subprocess commands.

Prevents command injection by enforcing strict regex patterns on all
values that flow into terraform/gcloud subprocess calls.
"""

import re

from fastapi import HTTPException

# Strict patterns for GCP identifiers
GCP_PROJECT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9\-]{4,28}[a-z0-9]$")
GCP_FOLDER_ID_PATTERN = re.compile(r"^\d{1,20}$")
GCP_ORG_ID_PATTERN = re.compile(r"^\d{1,20}$")

# Broad pattern for resource names (GCP and AWS)
RESOURCE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-.:/@]{0,255}$")

# AWS identifiers
AWS_ACCOUNT_ID_PATTERN = re.compile(r"^\d{12}$")
AWS_REGION_PATTERN = re.compile(r"^[a-z]{2}-[a-z]+-\d$")
AWS_ACCESS_KEY_PATTERN = re.compile(r"^[A-Z0-9]{16,128}$")

# GCS bucket name
GCS_BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._\-]{1,220}[a-z0-9]$")

# Generic safe string (no shell metacharacters)
SAFE_STRING_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-./: ]{0,500}$")


def validate_gcp_project_id(value: str) -> str:
    """Validate a GCP project ID."""
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Project ID cannot be empty")
    if not GCP_PROJECT_ID_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid GCP Project ID '{value}'. Must be 6-30 characters, lowercase letters, digits, and hyphens.",
        )
    return value


def validate_gcp_scope_id(scope_type: str, value: str) -> str:
    """Validate a GCP scope ID based on type."""
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Scope ID cannot be empty")

    if scope_type == "project":
        if not GCP_PROJECT_ID_PATTERN.match(value):
            raise HTTPException(status_code=400, detail=f"Invalid Project ID '{value}'.")
    elif scope_type == "folder":
        if not GCP_FOLDER_ID_PATTERN.match(value):
            raise HTTPException(status_code=400, detail=f"Invalid Folder ID '{value}'. Must be numeric.")
    elif scope_type == "organization":
        if not GCP_ORG_ID_PATTERN.match(value):
            raise HTTPException(status_code=400, detail=f"Invalid Organization ID '{value}'. Must be numeric.")
    return value


def validate_bucket_name(value: str) -> str:
    """Validate a GCS/S3 bucket name."""
    value = value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="Bucket name cannot be empty")
    if not GCS_BUCKET_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid bucket name '{value}'. Must be lowercase, 3-222 chars, letters/digits/hyphens/dots.",
        )
    return value


def validate_resource_name(value: str) -> str:
    """Validate a resource name/ID that may be passed to subprocess."""
    if not value:
        return value
    if not RESOURCE_NAME_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid resource name '{value[:50]}'. Contains disallowed characters.",
        )
    return value


def validate_aws_region(value: str) -> str:
    """Validate an AWS region."""
    value = value.strip()
    if not AWS_REGION_PATTERN.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid AWS region '{value}'.")
    return value


def validate_safe_string(value: str, field_name: str = "value") -> str:
    """Validate a generic string is safe for subprocess use."""
    if not value:
        return value
    if not SAFE_STRING_PATTERN.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: contains disallowed characters.",
        )
    return value
