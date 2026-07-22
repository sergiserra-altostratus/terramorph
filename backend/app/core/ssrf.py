"""SSRF protection for AI provider endpoint URLs.

Validates that custom AI provider URLs (Ollama, Azure OpenAI, etc.)
don't point to internal networks, cloud metadata services, or other
dangerous destinations.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

from app.core.logging import get_logger

logger = get_logger("security.ssrf")

# Known safe AI provider domains
ALLOWED_DOMAINS = {
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "api.groq.com",
    "api.mistral.ai",
    "bedrock-runtime.amazonaws.com",
    "localhost",
    "127.0.0.1",
}

# Allowed domain suffixes (for regional endpoints)
ALLOWED_SUFFIXES = (
    ".openai.azure.com",
    ".amazonaws.com",
    ".googleapis.com",
    ".anthropic.com",
    ".mistral.ai",
    ".groq.com",
)

# Blocked IP ranges (RFC 1918, link-local, metadata services)
BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS/GCP metadata)
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("fd00::/8"),         # IPv6 private
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]

# Specific blocked IPs (cloud metadata endpoints)
BLOCKED_IPS = {
    "169.254.169.254",  # AWS/GCP metadata service
    "metadata.google.internal",
}


def validate_ai_endpoint_url(url: str) -> str:
    """Validate an AI provider endpoint URL is safe.

    Args:
        url: The URL to validate.

    Returns:
        The validated URL.

    Raises:
        HTTPException: If the URL is potentially dangerous.
    """
    if not url or not url.strip():
        return ""

    url = url.strip()

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    # Must be http or https
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="URL must use http:// or https:// scheme.")

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL must contain a valid hostname.")

    # Check against blocked IPs directly
    if hostname in BLOCKED_IPS:
        logger.warning(f"SSRF blocked: {url} → metadata service")
        raise HTTPException(status_code=400, detail="URL points to a blocked address (cloud metadata service).")

    # Allow known safe domains
    if hostname in ALLOWED_DOMAINS:
        return url

    # Allow known safe suffixes
    if any(hostname.endswith(suffix) for suffix in ALLOWED_SUFFIXES):
        return url

    # For unknown domains, resolve and check IP
    try:
        resolved_ips = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in resolved_ips:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                for blocked_range in BLOCKED_RANGES:
                    if ip in blocked_range:
                        logger.warning(f"SSRF blocked: {url} → resolves to internal IP {ip_str}")
                        raise HTTPException(
                            status_code=400,
                            detail=f"URL resolves to a blocked internal IP address ({ip_str}). Only public endpoints are allowed.",
                        )
            except ValueError:
                pass
    except socket.gaierror:
        # Can't resolve — allow it (might be a Docker network name for Ollama)
        pass
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"SSRF check failed for {url}: {e}")

    return url
