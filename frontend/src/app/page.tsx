"use client";

import { useEffect, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  XCircle,
  Search,
  Code,
  Upload,
  RefreshCw,
  Network,
  Server,
  Globe,
  Database,
  HardDrive,
  Container,
  Shield,
  Zap,
  Key,
} from "lucide-react";
import Link from "next/link";
import { apiClient, type HealthResponse } from "@/lib/api";

interface StatusInfo {
  gcp: boolean;
  aws: boolean;
  ai: boolean;
  aiProvider: string | null;
}

const gcpResources = [
  { name: "Compute Engine", icon: Server },
  { name: "VPC Networks", icon: Globe },
  { name: "Cloud Storage", icon: HardDrive },
  { name: "Cloud SQL", icon: Database },
  { name: "GKE", icon: Container },
  { name: "Firewall Rules", icon: Shield },
  { name: "Cloud Run", icon: Zap },
  { name: "IAM", icon: Key },
];

const awsResources = [
  { name: "EC2", icon: Server },
  { name: "VPC", icon: Globe },
  { name: "S3", icon: HardDrive },
  { name: "RDS", icon: Database },
  { name: "EKS", icon: Container },
  { name: "Lambda", icon: Zap },
  { name: "IAM", icon: Shield },
  { name: "Route53", icon: Globe },
];

export default function DashboardPage() {
  const [status, setStatus] = useState<StatusInfo | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      apiClient.getHealth().catch(() => ({ gcp_authenticated: false })),
      apiClient.request<any>("/settings/ai/status").catch(() => ({ configured: false })),
      apiClient.request<any>("/settings/aws/status").catch(() => ({ configured: false })),
    ]).then(([health, ai, aws]) => {
      setStatus({
        gcp: (health as HealthResponse).gcp_authenticated || false,
        aws: aws.configured || false,
        ai: ai.configured || false,
        aiProvider: ai.provider || null,
      });
    });

    apiClient.request<any>("/history?limit=8")
      .then((data) => setJobs(data.jobs || []))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* System status bar */}
      <div className="flex items-center gap-4 text-xs">
        <StatusBadge label="GCP" ok={status?.gcp ?? null} />
        <StatusBadge label="AWS" ok={status?.aws ?? null} />
        <StatusBadge label="AI" ok={status?.ai ?? null} detail={status?.aiProvider || undefined} />
        <StatusBadge label="Terraform" ok={true} detail="v1.9+" />
      </div>

      {/* Pipeline — quick actions as a workflow */}
      <div>
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">Workflow</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
          <WorkflowStep href="/discover" step="1" icon={Search} label="Discover" description="Scan cloud resources" />
          <WorkflowStep href="/generate" step="2" icon={Code} label="Generate" description="Create Terraform HCL" />
          <WorkflowStep href="/auto-import" step="3" icon={Upload} label="Import" description="Import into state" />
          <WorkflowStep href="/drift" step="4" icon={RefreshCw} label="Drift Fix" description="Detect & fix drift" />
          <WorkflowStep href="/state-viz" step="5" icon={Network} label="Visualize" description="View dependencies" />
        </div>
      </div>

      {/* Supported resources */}
      <div>
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">Supported Resources</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {/* GCP */}
          <div className="rounded-md border border-border p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Google Cloud Platform</span>
              <span className="text-[11px] font-mono text-emerald-500">47+ types</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {gcpResources.map((r) => (
                <div key={r.name} className="flex flex-col items-center gap-1 py-2 rounded-md hover:bg-muted/50 transition-colors">
                  <r.icon className="w-4 h-4 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground text-center">{r.name}</span>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground mt-3 pt-3 border-t border-border">
              + Pub/Sub, DNS, BigQuery, Cloud Functions, Load Balancers, NAT, VPN, Cloud Armor, Secret Manager, KMS, Artifact Registry, Spanner, Dataflow, Composer, and more.
            </p>
          </div>

          {/* AWS */}
          <div className="rounded-md border border-border p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Amazon Web Services</span>
              <span className="text-[11px] font-mono text-emerald-500">20+ types</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {awsResources.map((r) => (
                <div key={r.name} className="flex flex-col items-center gap-1 py-2 rounded-md hover:bg-muted/50 transition-colors">
                  <r.icon className="w-4 h-4 text-muted-foreground" />
                  <span className="text-[10px] text-muted-foreground text-center">{r.name}</span>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground mt-3 pt-3 border-t border-border">
              + ELB, CloudFront, SQS, SNS, DynamoDB, ECS, Secrets Manager, CloudWatch, API Gateway, Elastic IPs.
            </p>
          </div>
        </div>
      </div>

      {/* Recent activity */}
      <div>
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">Recent Activity</h2>
        {jobs.length > 0 ? (
          <div className="rounded-md border border-border divide-y divide-border">
            {jobs.map((job: any, i: number) => (
              <div key={i} className="flex items-center justify-between px-4 py-2 text-sm">
                <div className="flex items-center gap-3">
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${job.status === "completed" ? "bg-emerald-500" : job.status === "failed" ? "bg-red-400" : "bg-zinc-400"}`} />
                  <span className="font-medium text-[13px]">{job.type || "Job"}</span>
                  {job.project && <span className="font-mono text-[11px] text-muted-foreground">{job.project}</span>}
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-[11px] font-mono ${job.status === "completed" ? "text-emerald-500" : job.status === "failed" ? "text-red-400" : "text-muted-foreground"}`}>
                    {job.status}
                  </span>
                  <span className="text-[11px] text-muted-foreground">{job.created_at ? new Date(job.created_at).toLocaleDateString() : ""}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-border p-6 text-center">
            <p className="text-sm text-muted-foreground">No recent activity</p>
            <p className="text-xs text-muted-foreground mt-1">Start by discovering resources in your cloud project.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ label, ok, detail }: { label: string; ok: boolean | null; detail?: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-1.5 h-1.5 rounded-full ${ok === null ? "bg-zinc-500" : ok ? "bg-emerald-500" : "bg-red-400"}`} />
      <span className="text-muted-foreground">{label}</span>
      {detail && <span className="text-foreground font-mono">{detail}</span>}
    </div>
  );
}

function WorkflowStep({ href, step, icon: Icon, label, description }: { href: string; step: string; icon: any; label: string; description: string }) {
  return (
    <Link
      href={href}
      className="group relative flex flex-col items-start rounded-md border border-border px-3 py-3 hover:border-emerald-500/30 hover:bg-muted/30 transition-colors"
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-mono text-muted-foreground">{step}</span>
        <Icon className="w-3.5 h-3.5 text-muted-foreground group-hover:text-emerald-500 transition-colors" />
      </div>
      <p className="text-sm font-medium group-hover:text-emerald-500 transition-colors">{label}</p>
      <p className="text-[11px] text-muted-foreground">{description}</p>
    </Link>
  );
}
