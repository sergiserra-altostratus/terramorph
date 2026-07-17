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
  Shield,
  Radio,
  Zap,
  MessageSquare,
  UserCog,
  Waypoints,
  MemoryStick,
  ArrowRight,
  BarChart3,
  Lock,
  Package,
  Key,
  Network,
  Timer,
  ChevronRight,
  BrainCircuit,
} from "lucide-react";
import { apiClient, type HealthResponse, type UsageStats } from "@/lib/api";
import { RESOURCE_TYPE_LABELS } from "@/types";
import type { ResourceType } from "@/types";

const resourceCards = [
  { name: "Compute Engine", icon: Server, color: "from-blue-500 to-blue-600", description: "VMs and instances" },
  { name: "VPC Networks", icon: Globe, color: "from-cyan-500 to-cyan-600", description: "Networks & subnets" },
  { name: "Cloud Storage", icon: HardDrive, color: "from-green-500 to-green-600", description: "GCS buckets" },
  { name: "Cloud SQL", icon: Database, color: "from-orange-500 to-orange-600", description: "Database instances" },
  { name: "GKE Clusters", icon: Container, color: "from-purple-500 to-purple-600", description: "Kubernetes" },
  { name: "Firewall Rules", icon: Shield, color: "from-red-500 to-red-600", description: "Network security" },
  { name: "Load Balancers", icon: Waypoints, color: "from-indigo-500 to-indigo-600", description: "Traffic routing" },
  { name: "Cloud Run", icon: Zap, color: "from-teal-500 to-teal-600", description: "Serverless containers" },
  { name: "Cloud Functions", icon: Radio, color: "from-yellow-500 to-yellow-600", description: "FaaS" },
  { name: "Pub/Sub", icon: MessageSquare, color: "from-pink-500 to-pink-600", description: "Messaging" },
  { name: "Service Accounts", icon: UserCog, color: "from-slate-500 to-slate-600", description: "IAM identities" },
  { name: "Cloud DNS", icon: Globe, color: "from-emerald-500 to-emerald-600", description: "DNS zones" },
  { name: "Memorystore", icon: MemoryStick, color: "from-rose-500 to-rose-600", description: "Redis instances" },
  { name: "IAM & Roles", icon: Shield, color: "from-amber-500 to-amber-600", description: "Bindings & custom roles" },
  { name: "BigQuery", icon: Database, color: "from-blue-600 to-indigo-600", description: "Data warehouse" },
  { name: "Secret Manager", icon: Lock, color: "from-gray-600 to-gray-700", description: "Secrets metadata" },
  { name: "Artifact Registry", icon: Package, color: "from-violet-500 to-violet-600", description: "Container images" },
  { name: "Cloud KMS", icon: Key, color: "from-zinc-500 to-zinc-600", description: "Encryption keys" },
  { name: "Cloud NAT", icon: Network, color: "from-sky-500 to-sky-600", description: "NAT gateways" },
  { name: "Cloud Scheduler", icon: Timer, color: "from-lime-600 to-lime-700", description: "Cron jobs" },
];

interface AIInfo {
  configured: boolean;
  active: string | null;
  count: number;
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [aiInfo, setAiInfo] = useState<AIInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiClient.getHealth().catch(() => null),
      apiClient.getStats().catch(() => null),
      apiClient.getAISettings().catch(() => null),
    ]).then(([h, s, ai]) => {
      setHealth(h);
      setStats(s);
      if (ai) {
        const configuredProviders = ai.providers.filter((p: any) => p.configured);
        setAiInfo({
          configured: ai.is_configured,
          active: ai.active_provider,
          count: configuredProviders.length,
        });
      }
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero section — subtle, not overwhelming */}
      <section className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-indigo-500/90 via-violet-500/90 to-purple-600/90 p-8 lg:p-10">
        {/* Subtle grid pattern overlay */}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyek0zNiAyNHYySDI0di0yaDEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30" />
        {/* Subtle glow */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-white/5 rounded-full blur-3xl" />

        <div className="relative z-10">
          <p className="text-sm font-medium text-white/70 mb-2 tracking-wide uppercase">
            Dashboard
          </p>
          <h1 className="text-2xl lg:text-3xl font-semibold text-white tracking-[-0.025em] mb-2">
            Welcome back
          </h1>
          <p className="text-base text-white/60 max-w-lg">
            Scan your GCP infrastructure and generate production-ready Terraform configurations.
          </p>
          <a
            href="/discover"
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 px-4 py-2.5 text-sm font-medium text-white hover:bg-white/20 active:scale-[0.98] transition-all duration-150"
          >
            Start Discovering <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </section>

      {/* System Status */}
      <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 animate-slide-up">
        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
          System Status
        </h3>
        {loading ? (
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
            <span className="text-sm text-gray-500 dark:text-gray-400">Checking connection...</span>
          </div>
        ) : health ? (
          <>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">API Connected</span>
            </div>
            <div className="flex items-center gap-2">
              {health.gcp_authenticated ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">GCP Authenticated</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-rose-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">GCP Not Authenticated</span>
                </>
              )}
            </div>
            <span className="ml-auto text-xs font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 px-2.5 py-0.5 rounded-full">
              v{health.version}
            </span>
          </div>
          {/* AI Provider Status */}
          {aiInfo && (
            <div className="flex items-center gap-6 mt-3 pt-3 border-t border-gray-100 dark:border-white/[0.04]">
              <div className="flex items-center gap-2">
                {aiInfo.configured ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">AI Enabled</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-gray-300 dark:text-gray-600" />
                    <span className="text-sm text-gray-500 dark:text-gray-400">AI Not Configured</span>
                  </>
                )}
              </div>
              {aiInfo.configured && aiInfo.active && (
                <div className="flex items-center gap-2">
                  <BrainCircuit className="h-3.5 w-3.5 text-violet-500" />
                  <span className="text-xs text-gray-600 dark:text-gray-300">
                    Active: <span className="font-medium">{aiInfo.active}</span>
                    {aiInfo.count > 1 && (
                      <span className="text-gray-400 dark:text-gray-500"> (+{aiInfo.count - 1} more)</span>
                    )}
                  </span>
                </div>
              )}
              {!aiInfo.configured && (
                <a href="/settings" className="text-xs text-primary hover:underline">
                  Configure →
                </a>
              )}
            </div>
          )}
          </>
        ) : (
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-rose-500" />
            <span className="text-sm text-gray-700 dark:text-gray-300">Backend not reachable</span>
          </div>
        )}
      </div>

      {/* Usage Statistics */}
      {stats && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <BarChart3 className="h-3.5 w-3.5" />
              Generation Statistics
            </h3>
            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <span>
                <span className="font-semibold text-gray-900 dark:text-white">{stats.total_generated}</span> resources generated
              </span>
              <span>
                <span className="font-semibold text-gray-900 dark:text-white">{stats.total_jobs}</span> jobs run
              </span>
            </div>
          </div>

          {stats.total_generated === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-white/[0.04] flex items-center justify-center mx-auto mb-3">
                <BarChart3 className="h-6 w-6 text-gray-300 dark:text-gray-600" />
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400">No resources generated yet.</p>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Run a discovery and generate Terraform code to see usage statistics here.
              </p>
            </div>
          ) : (
            <>
              {/* Bar Chart */}
              <div className="space-y-2.5">
                {Object.entries(stats.by_resource_type).slice(0, 8).map(([type, count]) => {
                  const maxCount = Math.max(...Object.values(stats.by_resource_type));
                  const percentage = (count / maxCount) * 100;
                  const label = RESOURCE_TYPE_LABELS[type as ResourceType] || type.replace(/_/g, " ");
                  return (
                    <div key={type} className="flex items-center gap-3">
                      <span className="text-xs text-gray-500 dark:text-gray-400 w-32 truncate text-right">{label}</span>
                      <div className="flex-1 h-6 bg-gray-100 dark:bg-white/[0.04] rounded-md overflow-hidden relative">
                        <div
                          className="h-full rounded-md bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-700 ease-out"
                          style={{ width: `${percentage}%` }}
                        />
                        <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-gray-600 dark:text-gray-300">
                          {count}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Recent Activity */}
              {stats.recent_jobs.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-100 dark:border-white/[0.04]">
                  <h4 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Recent Activity</h4>
                  <div className="flex gap-1.5">
                    {stats.recent_jobs.slice(-20).map((job, idx) => (
                      <div key={idx} className="flex-1 group relative">
                        <div
                          className="w-full rounded-sm bg-gradient-to-t from-indigo-500 to-violet-500 opacity-50 hover:opacity-100 transition-opacity cursor-default"
                          style={{ height: `${Math.max(8, Math.min(40, job.total_resources * 2))}px` }}
                        />
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block whitespace-nowrap rounded-md bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-[9px] px-1.5 py-0.5 z-10">
                          {job.total_resources} resources
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Supported Resources Grid */}
      <div className="animate-slide-up">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white tracking-tight mb-4">
          Supported Resources
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 stagger-children">
          {resourceCards.map((card) => (
            <div
              key={card.name}
              className="group relative rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-4 transition-all duration-200 hover:border-gray-300 dark:hover:border-white/[0.1] hover:shadow-md cursor-default"
            >
              {/* Subtle top accent line */}
              <div className="absolute top-0 left-4 right-4 h-px bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="flex items-center gap-3">
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br ${card.color} shadow-sm`}>
                  <card.icon className="h-4 w-4 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{card.name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{card.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Start */}
      <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-6 animate-slide-up">
        <h3 className="text-base font-semibold text-gray-900 dark:text-white tracking-tight mb-4">
          Quick Start
        </h3>
        <ol className="space-y-3.5 text-sm text-gray-600 dark:text-gray-300">
          <li className="flex items-start gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-[10px] font-bold text-white flex-shrink-0 shadow-sm">
              1
            </span>
            <span>
              Ensure GCP credentials are configured:{" "}
              <code className="rounded-md bg-gray-100 dark:bg-white/[0.06] px-1.5 py-0.5 text-xs font-mono text-gray-700 dark:text-gray-300">
                gcloud auth application-default login
              </code>
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-[10px] font-bold text-white flex-shrink-0 shadow-sm">
              2
            </span>
            <span>Navigate to Discover and select your project, folder, or organization scope</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-[10px] font-bold text-white flex-shrink-0 shadow-sm">
              3
            </span>
            <span>Choose which resource types to scan and start discovery</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-[10px] font-bold text-white flex-shrink-0 shadow-sm">
              4
            </span>
            <span>Review results, generate Terraform code, and download the import script</span>
          </li>
        </ol>
      </div>
    </div>
  );
}
