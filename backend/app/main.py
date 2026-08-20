"""Terramorph FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import discovery, generation, health, projects
from app.api.routes import settings as ai_settings_routes
from app.api.routes import drift as drift_routes
from app.api.routes import bulk_export as bulk_export_routes
from app.api.routes import aws_discovery as aws_routes
from app.api.routes import auto_import as auto_import_routes
from app.api.routes import state_viz as state_viz_routes
from app.api.ws import discovery_ws
from app.api.ws import drift_ws
from app.api.ws import auto_import_ws
from app.config import settings
from app.core.logging import setup_logging
from app.core.error_handler import register_error_handlers
from app.core.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler with graceful shutdown."""
    setup_logging()

    from app.core.logging import get_logger
    logger = get_logger("lifecycle")
    logger.info("Terramorph starting up...")

    yield

    # --- Graceful shutdown ---
    logger.info("Shutting down gracefully...")

    # 1. Cancel all running drift jobs and notify subscribers
    from app.services.drift import _drift_jobs, _drift_subscribers
    for job_id, job in list(_drift_jobs.items()):
        if job.get("status") == "running":
            job["cancel_requested"] = True
            logger.info(f"Cancelling drift job {job_id}")

    # 2. Cancel all running auto-import jobs
    from app.services.auto_import import _auto_import_jobs, _auto_import_subscribers
    for job_id, job in list(_auto_import_jobs.items()):
        if job.get("status") == "running":
            job["cancel_requested"] = True
            logger.info(f"Cancelling auto-import job {job_id}")

    # 3. Give running tasks a moment to notice cancellation
    import asyncio
    await asyncio.sleep(1)

    # 4. Clear subscriber queues (unblocks WebSocket loops)
    for job_id, queues in list(_drift_subscribers.items()):
        for queue in queues:
            try:
                queue.put_nowait({"type": "complete", "data": {"status": "shutdown", "message": "Server shutting down."}})
            except Exception:
                pass
    _drift_subscribers.clear()

    for job_id, queues in list(_auto_import_subscribers.items()):
        for queue in queues:
            try:
                queue.put_nowait({"type": "complete", "data": {"status": "shutdown", "message": "Server shutting down."}})
            except Exception:
                pass
    _auto_import_subscribers.clear()

    logger.info("Graceful shutdown complete.")


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

# Register centralized error handlers
register_error_handlers(app)

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

# Rate limiting on expensive endpoints
app.add_middleware(RateLimitMiddleware)

# API routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(discovery.router, prefix="/api/v1", tags=["discovery"])
app.include_router(generation.router, prefix="/api/v1", tags=["generation"])
app.include_router(ai_settings_routes.router, prefix="/api/v1", tags=["settings"])
app.include_router(drift_routes.router, prefix="/api/v1", tags=["drift"])
app.include_router(bulk_export_routes.router, prefix="/api/v1", tags=["bulk-export"])
app.include_router(aws_routes.router, prefix="/api/v1", tags=["aws"])
app.include_router(auto_import_routes.router, prefix="/api/v1", tags=["auto-import"])
app.include_router(state_viz_routes.router, prefix="/api/v1", tags=["state-viz"])

# WebSocket
app.include_router(discovery_ws.router, tags=["websocket"])
app.include_router(drift_ws.router, tags=["websocket"])
app.include_router(auto_import_ws.router, tags=["websocket"])
