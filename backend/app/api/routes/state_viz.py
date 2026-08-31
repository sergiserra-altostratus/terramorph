"""Terraform state visualization endpoint.

Parses terraform graph output (DOT format) and returns a JSON structure
of nodes and edges for the frontend to render as an interactive graph.
"""

import asyncio
import os
import re
import tempfile
import shutil

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.drift import _terraform_env

logger = get_logger("state_viz")

router = APIRouter()


class StateVizRequest(BaseModel):
    """Request to generate state visualization."""
    tf_files: dict[str, str] = Field(description="Dict of filename → HCL content")
    bucket: str = Field(default="", description="GCS bucket for remote state (optional)")
    prefix: str = Field(default="", description="State prefix (optional)")
    project_id: str = Field(default="", description="GCP project ID")


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # resource, data, provider, var, output, module
    resource_type: str | None = None


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def _parse_dot_graph(dot_output: str) -> tuple[list[dict], list[dict]]:
    """Parse DOT format from terraform graph into nodes and edges."""
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()

    for line in dot_output.split("\n"):
        line = line.strip()

        # Parse edges: "node1" -> "node2"
        edge_match = re.match(r'"([^"]+)"\s*->\s*"([^"]+)"', line)
        if edge_match:
            source = edge_match.group(1)
            target = edge_match.group(2)
            edges.append({"source": source, "target": target})

            # Auto-create nodes from edges
            for node_id in (source, target):
                if node_id not in seen_nodes:
                    seen_nodes.add(node_id)
                    nodes.append(_classify_node(node_id))
            continue

        # Parse standalone nodes: "node_name" [label = "..."]
        node_match = re.match(r'"([^"]+)"\s*[\[;]?', line)
        if node_match and "->" not in line and "{" not in line and "}" not in line:
            node_id = node_match.group(1)
            if node_id not in seen_nodes and not node_id.startswith("["):
                seen_nodes.add(node_id)
                nodes.append(_classify_node(node_id))

    return nodes, edges


def _classify_node(node_id: str) -> dict:
    """Classify a node by its ID pattern."""
    # Filter out meta nodes
    if node_id.startswith("[root]"):
        node_id = node_id.replace("[root] ", "")

    # Determine type
    if node_id.startswith("provider["):
        return {"id": node_id, "label": node_id, "type": "provider", "resource_type": None}
    elif node_id.startswith("data."):
        parts = node_id.split(".")
        resource_type = parts[1] if len(parts) > 1 else None
        return {"id": node_id, "label": node_id, "type": "data", "resource_type": resource_type}
    elif node_id.startswith("var."):
        return {"id": node_id, "label": node_id, "type": "var", "resource_type": None}
    elif node_id.startswith("output."):
        return {"id": node_id, "label": node_id, "type": "output", "resource_type": None}
    elif node_id.startswith("module."):
        return {"id": node_id, "label": node_id, "type": "module", "resource_type": None}
    else:
        # Resource: type.name
        parts = node_id.split(".")
        resource_type = parts[0] if len(parts) > 1 else None
        label = parts[-1] if len(parts) > 1 else node_id
        return {"id": node_id, "label": label, "type": "resource", "resource_type": resource_type}


@router.post("/state/graph")
async def get_state_graph(request: StateVizRequest) -> dict:
    """Generate a dependency graph from Terraform files.

    Runs `terraform graph` and returns nodes/edges for visualization.
    """
    if not request.tf_files:
        raise HTTPException(status_code=400, detail="No Terraform files provided.")

    work_dir = tempfile.mkdtemp(prefix="terramorph-graph-")

    try:
        # Write files (skip backend.tf — not needed for graph, causes init issues)
        for filename, content in request.tf_files.items():
            if filename.lower() == "backend.tf":
                continue
            with open(os.path.join(work_dir, filename), "w") as f:
                f.write(content)

        # Write minimal provider if not present
        if "provider.tf" not in request.tf_files:
            provider_content = '''terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
  }
}
'''
            with open(os.path.join(work_dir, "provider.tf"), "w") as f:
                f.write(provider_content)

        # terraform init (required for graph)
        process = await asyncio.create_subprocess_exec(
            "terraform", "init", "-no-color", "-backend=false",
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_terraform_env(),
        )
        await asyncio.wait_for(process.wait(), timeout=120)

        if process.returncode != 0:
            stderr = (await process.stderr.read()).decode()
            raise HTTPException(status_code=422, detail=f"terraform init failed: {stderr[:500]}")

        # terraform graph
        process = await asyncio.create_subprocess_exec(
            "terraform", "graph", "-no-color",
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_terraform_env(),
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=30
        )

        if process.returncode != 0:
            raise HTTPException(status_code=422, detail=f"terraform graph failed: {stderr_bytes.decode()[:500]}")

        dot_output = stdout_bytes.decode()
        nodes, edges = _parse_dot_graph(dot_output)

        # Filter out meta/internal nodes
        nodes = [n for n in nodes if n["type"] in ("resource", "data", "module")]
        valid_ids = {n["id"] for n in nodes}
        edges = [e for e in edges if e["source"] in valid_ids and e["target"] in valid_ids]

        return {
            "nodes": nodes,
            "edges": edges,
            "total_resources": len([n for n in nodes if n["type"] == "resource"]),
            "total_data_sources": len([n for n in nodes if n["type"] == "data"]),
        }

    except HTTPException:
        raise
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Timeout generating graph.")
    except Exception as e:
        logger.error(f"State graph generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
