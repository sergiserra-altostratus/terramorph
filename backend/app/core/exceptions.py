"""Custom application exceptions."""


class TerramorphError(Exception):
    """Base exception for Terramorph."""

    pass


class CredentialError(TerramorphError):
    """GCP credential error."""

    pass


class DiscoveryError(TerramorphError):
    """Error during resource discovery."""

    pass


class GenerationError(TerramorphError):
    """Error during HCL code generation."""

    pass


class JobNotFoundError(TerramorphError):
    """Job ID not found."""

    pass
