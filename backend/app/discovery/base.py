"""Abstract base class for resource discoverers."""

from abc import ABC, abstractmethod

from google.auth.credentials import Credentials

from app.models.resources import DiscoveredResource


class BaseDiscoverer(ABC):
    """Abstract base for GCP resource discoverers."""

    def __init__(self, credentials: Credentials):
        self.credentials = credentials

    @abstractmethod
    async def discover(self, project_id: str) -> list[DiscoveredResource]:
        """Discover resources in a GCP project.

        Args:
            project_id: The GCP project ID to scan.

        Returns:
            List of discovered resources.
        """
        ...

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize a resource name for use as a Terraform resource name.

        Replaces hyphens and dots with underscores, strips leading digits.
        """
        sanitized = name.replace("-", "_").replace(".", "_")
        if sanitized and sanitized[0].isdigit():
            sanitized = f"r_{sanitized}"
        return sanitized
