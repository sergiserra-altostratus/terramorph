"""Tests for HCL generation functionality."""

from app.generation.hcl_renderer import HCLRenderer
from app.generation.import_generator import ImportGenerator
from app.models.resources import DiscoveredResource, ResourceType


def _make_resource(
    name: str = "test-vm",
    resource_type: ResourceType = ResourceType.COMPUTE_INSTANCE,
    attributes: dict | None = None,
) -> DiscoveredResource:
    """Helper to create a test resource."""
    return DiscoveredResource(
        id="test-id-001",
        type=resource_type,
        name=name,
        project="my-project",
        location="us-central1-a",
        terraform_resource_type="google_compute_instance",
        terraform_resource_name="test_vm",
        terraform_import_id="projects/my-project/zones/us-central1-a/instances/test-vm",
        attributes=attributes
        or {
            "machine_type": "e2-medium",
            "zone": "us-central1-a",
            "status": "RUNNING",
            "network_interfaces": [{"network": "default", "subnetwork": "default"}],
            "disks": [{"boot": True, "auto_delete": True, "source": "debian-11"}],
            "tags": ["http-server"],
            "labels": {"env": "production"},
            "metadata": {},
        },
    )


def test_render_provider():
    """Test provider.tf generation."""
    renderer = HCLRenderer()
    content = renderer.render_provider("my-project")
    assert 'project = "my-project"' in content
    assert "hashicorp/google" in content
    assert "required_version" in content


def test_render_compute_instance():
    """Test compute instance HCL generation."""
    renderer = HCLRenderer()
    resource = _make_resource()
    content = renderer.render_resource(resource)
    assert "google_compute_instance" in content
    assert "test_vm" in content
    assert "e2-medium" in content
    assert "us-central1-a" in content


def test_render_by_type():
    """Test resources are grouped by type into separate files."""
    renderer = HCLRenderer()
    resources = [
        _make_resource("vm-1"),
        _make_resource("vm-2"),
    ]
    files = renderer.render_by_type(resources)
    assert "compute.tf" in files
    assert "google_compute_instance" in files["compute.tf"]


def test_import_generator():
    """Test import script generation."""
    gen = ImportGenerator()
    resources = [_make_resource()]
    content = gen.generate(resources)
    assert "#!/bin/bash" in content
    assert "terraform import" in content
    assert "google_compute_instance.test_vm" in content
    assert "projects/my-project/zones/us-central1-a/instances/test-vm" in content
