"""Terramorph FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import discovery, generation, health, projects
from app.api.routes import settings as ai_settings_routes
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
    description="Reverse Terraform - Discover GCP infrastructure and generate Terraform code",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(discovery.router, prefix="/api/v1", tags=["discovery"])
app.include_router(generation.router, prefix="/api/v1", tags=["generation"])
app.include_router(ai_settings_routes.router, prefix="/api/v1", tags=["settings"])

# WebSocket
app.include_router(discovery_ws.router, tags=["websocket"])
