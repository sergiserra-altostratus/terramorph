"""GCP Application Default Credentials handler."""

import google.auth
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError

from app.core.exceptions import CredentialError


def get_credentials() -> Credentials:
    """Get GCP credentials via Application Default Credentials.

    Returns:
        Authenticated credentials object.

    Raises:
        CredentialError: If ADC is not configured or invalid.
    """
    try:
        credentials, project = google.auth.default()
        return credentials
    except DefaultCredentialsError as e:
        raise CredentialError(
            "GCP Application Default Credentials not configured. "
            "Run 'gcloud auth application-default login' or set "
            "GOOGLE_APPLICATION_CREDENTIALS environment variable."
        ) from e


def get_default_project() -> str | None:
    """Get the default project from ADC."""
    try:
        _, project = google.auth.default()
        return project
    except DefaultCredentialsError:
        return None


def check_authentication() -> dict:
    """Check if GCP authentication is valid.

    Returns:
        Dictionary with authentication status details.
    """
    try:
        credentials, project = google.auth.default()
        return {
            "authenticated": True,
            "project": project,
            "account": getattr(credentials, "service_account_email", None),
        }
    except DefaultCredentialsError:
        return {
            "authenticated": False,
            "project": None,
            "account": None,
        }
