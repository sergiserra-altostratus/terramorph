# Terramorph Architecture

## Overview

Terramorph is a reverse Terraform tool that discovers existing GCP infrastructure,
generates Terraform HCL code, and creates import scripts to bring resources under
Terraform state management.

## Component Architecture

```
┌──────────────────┐         ┌──────────────────────────────────────┐
│   CLI (Rust)     │────────▶│         Backend API (FastAPI)         │
└──────────────────┘  HTTP   │                                      │
                             │  ┌────────────┐  ┌────────────────┐  │
┌──────────────────┐         │  │ Discovery  │  │   Generation   │  │
│ Frontend (Next)  │────────▶│  │  Engine    │  │    Engine      │  │
└──────────────────┘  HTTP   │  └─────┬──────┘  └───────┬────────┘  │
                             └────────┼──────────────────┼───────────┘
                                      │                  │
                                      ▼                  ▼
                             ┌────────────────┐  ┌──────────────┐
                             │  GCP APIs      │  │ Jinja2 HCL   │
                             │  (via ADC)     │  │ Templates    │
                             └────────────────┘  └──────────────┘
```

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Backend | Python 3.12 + FastAPI | Async, GCP SDK native, Pydantic validation |
| Frontend | Next.js 14 + React + TypeScript + Tailwind | Modern, SSR, excellent DX |
| CLI | Rust + clap | Fast binary, no runtime deps |
| Templates | Jinja2 | Native Python, ideal for HCL text generation |
| State | In-memory dict | MVP simplicity, upgrade path to Redis |

## Security Model

- Zero credential storage: ADC mounted read-only
- No write operations to GCP
- Non-root containers
- No secrets in Docker images

## API Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/auth/status` - GCP auth status
- `GET /api/v1/projects` - List accessible projects
- `POST /api/v1/discovery/start` - Start resource discovery
- `GET /api/v1/discovery/status/{job_id}` - Job progress
- `GET /api/v1/discovery/results/{job_id}` - Full results
- `POST /api/v1/generate/terraform` - Generate HCL code
- `GET /api/v1/generate/download/{job_id}` - Download ZIP
- `WS /ws/discovery/{job_id}` - Real-time progress

## Data Flow

1. User selects scope (project/folder/org)
2. Backend discovers resources via GCP APIs
3. Resources normalized into Pydantic models
4. User triggers generation
5. Jinja2 templates render HCL
6. Import script generated
7. User downloads and runs `terraform import`
