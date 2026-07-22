"""Terramorph FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import discovery, generation, health, projects
from app.api.routes import settings as ai_settings_routes
from app.api.routes import drift as drift_routes
from app.api.routes import bulk_export as bulk_export_routes
from app.api.routes import aws_discovery as aws_routes
from app.api.ws import discovery_ws
from app.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    setup_logging()
    yield


app = FastAPI(
    title="Terramorph API",
    description="""
# Terramorph — Reverse Terraform API

Discover existing cloud infrastructure (GCP & AWS), generate production-ready
Terraform HCL code, and import resources into Terraform state.

## Features

- **Multi-cloud discovery** — Scan GCP (47 resource types) and AWS (20+ resource types)
- **Terraform generation** — Flat resources or official Google/AWS modules
- **AI code cleaning** — Remove defaults using OpenAI, Anthropic, Gemini, Ollama, and more
- **Drift detection** — AI-powered iterative fix until terraform plan shows no changes
- **Bulk Export** — Precise discovery via gcloud Cloud Asset API
- **Import blocks** — Native Terraform 1.5+ import {} syntax

## Authentication

When enabled (`TERRAMORPH_AUTH_DISABLED=false`), all endpoints except `/health`
require a Bearer token: `Authorization: Bearer <token>`

Get your token from `GET /api/v1/health/token`.
    """,
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "System health, auth status, onboarding, and job history"},
        {"name": "projects", "description": "List GCP projects accessible with current credentials"},
        {"name": "discovery", "description": "GCP resource discovery via Python SDKs"},
        {"name": "generation", "description": "Terraform HCL code generation (flat or modules)"},
        {"name": "settings", "description": "AI provider and AWS credential configuration"},
        {"name": "drift", "description": "Drift detection and AI-powered auto-fix"},
        {"name": "bulk-export", "description": "GCP Bulk Export via gcloud Cloud Asset API"},
        {"name": "aws", "description": "AWS resource discovery"},
        {"name": "websocket", "description": "Real-time progress streaming via WebSocket"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication middleware (disable with TERRAMORPH_AUTH_DISABLED=true)
from app.core.auth import AuthMiddleware
app.add_middleware(AuthMiddleware)

# API routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(discovery.router, prefix="/api/v1", tags=["discovery"])
app.include_router(generation.router, prefix="/api/v1", tags=["generation"])
app.include_router(ai_settings_routes.router, prefix="/api/v1", tags=["settings"])
app.include_router(drift_routes.router, prefix="/api/v1", tags=["drift"])
app.include_router(bulk_export_routes.router, prefix="/api/v1", tags=["bulk-export"])
app.include_router(aws_routes.router, prefix="/api/v1", tags=["aws"])

# WebSocket
app.include_router(discovery_ws.router, tags=["websocket"])
