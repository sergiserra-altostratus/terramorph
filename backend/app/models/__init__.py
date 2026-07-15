"""Pydantic models for request/response schemas."""

from app.models.discovery import (
    DiscoveryRequest,
    DiscoveryResult,
    DiscoveryStatus,
    JobProgress,
)
from app.models.generation import GenerationRequest, GenerationResult, GeneratedFile
from app.models.resources import (
    DiscoveredResource,
    ResourceSummary,
    ResourceType,
    ScopeConfig,
    ScopeType,
)

__all__ = [
    "DiscoveredResource",
    "DiscoveryRequest",
    "DiscoveryResult",
    "DiscoveryStatus",
    "GeneratedFile",
    "GenerationRequest",
    "GenerationResult",
    "JobProgress",
    "ResourceSummary",
    "ResourceType",
    "ScopeConfig",
    "ScopeType",
]
