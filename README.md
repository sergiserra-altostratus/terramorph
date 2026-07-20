# Terramorph

**Reverse Terraform** — Discover existing GCP infrastructure, generate Terraform HCL code, and import resources into Terraform state.

## Overview

Terramorph scans your Google Cloud Platform projects and automatically generates production-ready Terraform configuration files. It bridges the gap between manually created infrastructure and Infrastructure as Code (IaC).

### Supported Resources (MVP)

- Compute Engine instances
- VPC Networks & Subnets
- Cloud Storage buckets
- Cloud SQL instances
- GKE clusters

## Quick Start

### Prerequisites

- Docker & Docker Compose
- GCP credentials configured via Application Default Credentials:

```bash
gcloud auth application-default login
```

### Run with Docker Compose

```bash
# Copy environment file
cp .env.example .env

# Start production
make prod

# Or start development (with hot-reload)
make dev
```

Access the web UI at `http://localhost:3000`

### CLI Usage

```bash
# Build the CLI
make build-cli

# Discover resources in a project
./cli/target/release/terramorph discover --project my-gcp-project

# Generate Terraform code
./cli/target/release/terramorph generate --job-id <job-id> --output ./terraform/
```

## Architecture

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

## Required GCP Permissions

Minimum IAM roles for the authenticated user/service account:

- `roles/compute.viewer` — VM and network discovery
- `roles/storage.admin` — Bucket metadata listing
- `roles/cloudsql.viewer` — Cloud SQL instance discovery
- `roles/container.clusterViewer` — GKE cluster discovery
- `roles/resourcemanager.projectViewer` — Project enumeration

For organization/folder-level discovery:
- `roles/browser` — Organization hierarchy enumeration
- `roles/resourcemanager.folderViewer` — Folder listing

## Development

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# CLI
cd cli && cargo build
```

## Security

- **Zero credential storage** — ADC credentials are volume-mounted read-only, never persisted
- **Read-only operations** — Terramorph never modifies your GCP resources
- **Non-root containers** — All services run as unprivileged users
- **No secrets in images** — Only credential file paths are passed via environment

## Roadmap

Upcoming features and improvements planned for future releases:

- **AWS Support** — Extend discovery and generation to Amazon Web Services (EC2, S3, RDS, EKS, VPC, IAM, Lambda, and more)
- **Infrastructure from form** — Create new infrastructure directly from a visual form in the web UI, generating Terraform code without needing pre-existing resources (forward Terraform)
- **Multi-tenant SaaS mode** — OAuth-based authentication, team workspaces, and hosted deployment option

## License

MIT
