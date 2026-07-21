"""Base class for AWS resource discoverers."""

from abc import ABC, abstractmethod

import boto3

from app.models.resources import DiscoveredResource


class AWSBaseDiscoverer(ABC):
    """Abstract base for AWS resource discoverers."""

    def __init__(self, session: boto3.Session):
        self.session = session
        self.region = session.region_name

    @abstractmethod
    async def discover(self) -> list[DiscoveredResource]:
        """Discover resources in the AWS account."""
        ...

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize a resource name for Terraform."""
        sanitized = name.replace("-", "_").replace(".", "_").replace("/", "_")
        if sanitized and sanitized[0].isdigit():
            sanitized = f"r_{sanitized}"
        return sanitized
