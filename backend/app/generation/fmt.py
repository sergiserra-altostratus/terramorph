"""Terraform fmt integration for formatting generated HCL code."""

import shutil
import subprocess
import tempfile
import os

from app.core.logging import get_logger

logger = get_logger("generation.fmt")


def is_terraform_available() -> bool:
    """Check if terraform binary is available in PATH."""
    return shutil.which("terraform") is not None


def fmt_content(content: str) -> str:
    """Format HCL content using 'terraform fmt'.

    If terraform is not available, returns the content unchanged.

    Args:
        content: Raw HCL content to format.

    Returns:
        Formatted HCL content, or original if formatting fails.
    """
    if not is_terraform_available():
        logger.debug("terraform not available, skipping fmt")
        return content

    try:
        result = subprocess.run(
            ["terraform", "fmt", "-"],
            input=content,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout
        else:
            logger.warning(f"terraform fmt failed: {result.stderr}")
            return content
    except (subprocess.TimeoutExpired, OSError) as e:
        logger.warning(f"terraform fmt error: {e}")
        return content


def fmt_files(files: list[dict]) -> list[dict]:
    """Format all .tf files in a list of generated files.

    Args:
        files: List of dicts with 'filename' and 'content' keys.

    Returns:
        Same list with formatted content for .tf files.
    """
    if not is_terraform_available():
        logger.debug("terraform not available, skipping fmt for all files")
        return files

    formatted = []
    for file in files:
        if file["filename"].endswith(".tf"):
            formatted_content = fmt_content(file["content"])
            formatted.append({**file, "content": formatted_content})
        else:
            formatted.append(file)

    return formatted
