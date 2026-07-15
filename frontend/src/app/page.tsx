"use client";

import { useEffect, useState } from "react";
import {
  Server,
  Globe,
  Database,
  HardDrive,
  Container,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { apiClient, type HealthResponse } from "@/lib/api";

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  const resourceCards = [
    { name: "Compute Instances", icon: Server, description: "VMs and machine instances" },
    { name: "VPC Networks", icon: Globe, description: "Networks and subnets" },
    { name: "Cloud Storage", icon: HardDrive, description: "GCS buckets" },
    { name: "Cloud SQL", icon: Database, description: "Database instances" },
    { name: "GKE Clusters", icon: Container, description: "Kubernetes clusters" },
  ];

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Discover your GCP infrastructure and generate Terraform code.
        </p>
      </div>

      {/* Status Card */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-sm font-medium text-muted-foreground mb-4">
          System Status
        </h3>
        {loading ? (
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span className="text-sm">Checking connection...</span>
          </div>
        ) : health ? (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span className="text-sm">API Connected</span>
            </div>
            <div className="flex items-center gap-2">
              {health.gcp_authenticated ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <span className="text-sm">GCP Authenticated</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-destructive" />
                  <span className="text-sm">GCP Not Authenticated</span>
                </>
              )}
            </div>
            <span className="text-xs text-muted-foreground">
              v{health.version}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-destructive" />
            <span className="text-sm">Backend not reachable</span>
          </div>
        )}
      </div>

      {/* Resource Types */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Supported Resources</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {resourceCards.map((card) => (
            <div
              key={card.name}
              className="rounded-lg border bg-card p-4 hover:border-primary/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-secondary">
                  <card.icon className="h-5 w-5 text-secondary-foreground" />
                </div>
                <div>
                  <p className="text-sm font-medium">{card.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {card.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Start */}
      <div className="rounded-lg border bg-card p-6">
        <h3 className="text-lg font-semibold mb-2">Quick Start</h3>
        <ol className="space-y-2 text-sm text-muted-foreground list-decimal list-inside">
          <li>
            Ensure GCP credentials are configured:{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
              gcloud auth application-default login
            </code>
          </li>
          <li>Navigate to the Discover page and select your scope</li>
          <li>Choose which resource types to scan</li>
          <li>Review discovered resources and generate Terraform code</li>
          <li>Download the generated files and run the import script</li>
        </ol>
      </div>
    </div>
  );
}
