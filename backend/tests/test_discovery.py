"""Tests for discovery functionality."""

from app.discovery.base import BaseDiscoverer
from app.models.resources import ResourceType


def test_sanitize_name():
    """Test resource name sanitization."""
    assert BaseDiscoverer.sanitize_name("my-resource") == "my_resource"
    assert BaseDiscoverer.sanitize_name("my.resource.name") == "my_resource_name"
    assert BaseDiscoverer.sanitize_name("123-invalid") == "r_123_invalid"
    assert BaseDiscoverer.sanitize_name("valid_name") == "valid_name"


def test_resource_type_enum():
    """Test resource type values."""
    assert ResourceType.COMPUTE_INSTANCE == "compute_instance"
    assert ResourceType.VPC_NETWORK == "vpc_network"
    assert ResourceType.GCS_BUCKET == "gcs_bucket"
    assert ResourceType.CLOUD_SQL == "cloud_sql"
    assert ResourceType.GKE_CLUSTER == "gke_cluster"


def test_health_endpoint(client):
    """Test health check endpoint returns valid response."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "gcp_authenticated" in data
