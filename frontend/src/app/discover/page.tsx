"use client";

import { useState, useEffect } from "react";
import { Play, CheckCircle2, Loader2, AlertCircle, Search, Sparkles, Clock, X, ArrowRight } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { DiscoveryStatus, DiscoveryResult } from "@/lib/api";
import { ALL_RESOURCE_TYPES, RESOURCE_TYPE_LABELS } from "@/types";
import type { ResourceType, ScopeType } from "@/types";
import { ResourceTypeSelector } from "@/components/ResourceTypeSelector";
import { AWSResourceTypeSelector } from "@/components/AWSResourceTypeSelector";
import { GCPLogo, AWSLogo } from "@/components/CloudProviderLogos";

interface RecentScope {
  type: ScopeType;
  id: string;
  timestamp: number;
}

const RECENT_SCOPES_KEY = "terramorph_recent_scopes";
const MAX_RECENT = 8;

function loadRecentScopes(): RecentScope[] {
  if (typeof window === "undefined") return [];
  try {
    const data = localStorage.getItem(RECENT_SCOPES_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

function saveRecentScope(scope: RecentScope) {
  const existing = loadRecentScopes();
  const filtered = existing.filter((s) => !(s.type === scope.type && s.id === scope.id));
  const updated = [scope, ...filtered].slice(0, MAX_RECENT);
  localStorage.setItem(RECENT_SCOPES_KEY, JSON.stringify(updated));
  return updated;
}

function removeRecentScope(type: ScopeType, id: string): RecentScope[] {
  const existing = loadRecentScopes();
  const updated = existing.filter((s) => !(s.type === type && s.id === id));
  localStorage.setItem(RECENT_SCOPES_KEY, JSON.stringify(updated));
  return updated;
}

export default function DiscoverPage() {
  const [cloudProvider, setCloudProvider] = useState<"gcp" | "aws">("gcp");
  const [scopeType, setScopeType] = useState<ScopeType>("project");
  const [scopeId, setScopeId] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<ResourceType[]>([]);
  const [awsResourceTypes, setAwsResourceTypes] = useState<string[]>([]);
  const [awsConfigured, setAwsConfigured] = useState<boolean>(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<DiscoveryStatus | null>(null);
  const [result, setResult] = useState<DiscoveryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [recentScopes, setRecentScopes] = useState<RecentScope[]>([]);
  const [discoveryMode, setDiscoveryMode] = useState<"api" | "bulk_export">("api");
  const [bulkExportAvailable, setBulkExportAvailable] = useState<boolean | null>(null);
  const [bulkResult, setBulkResult] = useState<any>(null);
  const [apiCheck, setApiCheck] = useState<{ status: "idle" | "checking" | "done"; enabled?: boolean; message?: string }>({ status: "idle" });

  useEffect(() => {
    setRecentScopes(loadRecentScopes());
    apiClient.getBulkExportAvailability()
      .then((r) => setBulkExportAvailable(r.available))
      .catch(() => setBulkExportAvailable(false));
    apiClient.getAWSStatus()
      .then((r) => setAwsConfigured(r.configured))
      .catch(() => setAwsConfigured(false));
  }, []);

  // Check Cloud Asset API when mode is bulk_export and project ID changes
  useEffect(() => {
    if (discoveryMode !== "bulk_export" || !scopeId.trim() || scopeType !== "project") {
      setApiCheck({ status: "idle" });
      return;
    }
    const timer = setTimeout(async () => {
      setApiCheck({ status: "checking" });
      try {
        const result = await apiClient.checkCloudAssetAPI(scopeId.trim());
        setApiCheck({ status: "done", enabled: result.enabled, message: result.message || result.error });
      } catch {
        setApiCheck({ status: "done", enabled: false, message: "Unable to check API status" });
      }
    }, 800); // Debounce
    return () => clearTimeout(timer);
  }, [discoveryMode, scopeId, scopeType]);

  const applyRecentScope = (scope: RecentScope) => {
    setScopeType(scope.type);
    setScopeId(scope.id);
  };

  const deleteRecentScope = (type: ScopeType, id: string) => {
    const updated = removeRecentScope(type, id);
    setRecentScopes(updated);
  };

  const startDiscovery = async () => {
    if (cloudProvider === "aws") {
      if (!awsConfigured) { setError("AWS credentials not configured. Go to Settings."); return; }
      setError(null); setIsRunning(true); setResult(null); setBulkResult(null);
      try {
        const job = await apiClient.startAWSDiscovery({ resource_types: awsResourceTypes });
        setJobId(job.job_id);
        const pollInterval = setInterval(async () => {
          try {
            const s = await apiClient.getAWSDiscoveryStatus(job.job_id);
            setStatus(s);
            if (s.status === "completed") {
              clearInterval(pollInterval);
              const r = await apiClient.getAWSDiscoveryResults(job.job_id);
              setResult(r);
              setIsRunning(false);
            } else if (s.status === "failed") {
              clearInterval(pollInterval);
              setError("AWS discovery failed");
              setIsRunning(false);
            }
          } catch (e) {
            clearInterval(pollInterval);
            setError(e instanceof Error ? e.message : "Status check failed");
            setIsRunning(false);
          }
        }, 2000);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to start AWS discovery");
        setIsRunning(false);
      }
      return;
    }

    // GCP Discovery
    if (!scopeId.trim()) { setError("Please enter a scope ID"); return; }
    setError(null); setIsRunning(true); setResult(null); setBulkResult(null);

    const updated = saveRecentScope({ type: scopeType, id: scopeId.trim(), timestamp: Date.now() });
    setRecentScopes(updated);

    try {
      if (discoveryMode === "bulk_export") {
        // Bulk Export mode
        const job = await apiClient.startBulkExport({ project_id: scopeId.trim() });
        setJobId(job.job_id);

        const pollInterval = setInterval(async () => {
          try {
            const s = await apiClient.getBulkExportStatus(job.job_id);
            setStatus(s);
            if (s.status === "completed") {
              clearInterval(pollInterval);
              const r = await apiClient.getBulkExportResults(job.job_id);
              setBulkResult(r);
              setIsRunning(false);
            } else if (s.status === "failed") {
              clearInterval(pollInterval);
              setError(s.error || "Bulk export failed");
              setIsRunning(false);
            }
          } catch (e) {
            clearInterval(pollInterval);
            setError(e instanceof Error ? e.message : "Status check failed");
            setIsRunning(false);
          }
        }, 3000);
      } else {
        // API Discovery mode — use WebSocket for real-time progress
        const job = await apiClient.startDiscovery({
          scope: { type: scopeType, id: scopeId.trim() },
          resource_types: selectedTypes,
        });
        setJobId(job.job_id);
        setStatus({ job_id: job.job_id, status: "running", progress: { total: selectedTypes.length, completed: 0, current_type: null, message: "Connecting..." }, resources_found: 0, error: null });

        // Try WebSocket, fallback to polling after 5s timeout
        let wsConnected = false;
        const wsUrl = apiClient.getWebSocketUrl(job.job_id);
        let ws: WebSocket | null = null;

        try {
          ws = new WebSocket(wsUrl);
        } catch {
          ws = null;
        }

        // Fallback to polling function
        const startPolling = () => {
          const pollInterval = setInterval(async () => {
            try {
              const s = await apiClient.getDiscoveryStatus(job.job_id);
              setStatus(s);
              if (s.status === "completed") {
                clearInterval(pollInterval);
                const r = await apiClient.getDiscoveryResults(job.job_id);
                setResult(r);
                setIsRunning(false);
              } else if (s.status === "failed") {
                clearInterval(pollInterval);
                setError(s.error || "Discovery failed");
                setIsRunning(false);
              }
            } catch (e) {
              clearInterval(pollInterval);
              setError(e instanceof Error ? e.message : "Polling failed");
              setIsRunning(false);
            }
          }, 2000);
        };

        if (ws) {
          // Timeout: if WS doesn't send data in 10s, fallback to polling
          const wsTimeout = setTimeout(() => {
            if (!wsConnected && ws) {
              ws.close();
              startPolling();
            }
          }, 10000);

          ws.onmessage = async (event) => {
            wsConnected = true;
            clearTimeout(wsTimeout);
            const msg = JSON.parse(event.data);
            if (msg.type === "progress") {
              setStatus({ job_id: job.job_id, status: "running", progress: msg.data, resources_found: 0, error: null });
            } else if (msg.type === "complete") {
              ws?.close();
              const r = await apiClient.getDiscoveryResults(job.job_id);
              setResult(r);
              setIsRunning(false);
            }
          };

          ws.onerror = () => {
            clearTimeout(wsTimeout);
            ws?.close();
            startPolling();
          };

          ws.onclose = () => {
            if (!wsConnected) {
              clearTimeout(wsTimeout);
              startPolling();
            }
          };
        } else {
          startPolling();
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start discovery");
      setIsRunning(false);
    }
  };

  const scopeLabel = (type: ScopeType) => {
    switch (type) {
      case "project": return "Project";
      case "folder": return "Folder";
      case "organization": return "Organization";
    }
  };

  const scopeColor = (type: ScopeType) => {
    switch (type) {
      case "project": return "bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-200/60 dark:border-indigo-500/20";
      case "folder": return "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200/60 dark:border-amber-500/20";
      case "organization": return "bg-violet-50 dark:bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-200/60 dark:border-violet-500/20";
    }
  };

  const timeAgo = (ts: number) => {
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 shadow-sm">
          <Search className="h-4 w-4 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-[-0.025em] text-gray-900 dark:text-white">
            Discover Resources
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Scan your GCP infrastructure to find existing resources.
          </p>
        </div>
      </div>

      {/* Recent Scopes */}
      {recentScopes.length > 0 && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 animate-slide-up">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2 mb-3">
            <Clock className="h-3.5 w-3.5" />
            Recent Scopes
          </h3>
          <div className="flex flex-wrap gap-2">
            {recentScopes.map((scope) => (
              <div
                key={`${scope.type}-${scope.id}`}
                className="group relative flex items-center"
              >
                <button
                  onClick={() => applyRecentScope(scope)}
                  className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-all duration-150 hover:shadow-sm ${scopeColor(scope.type)}`}
                  disabled={isRunning}
                >
                  <span className="opacity-70">{scopeLabel(scope.type)}:</span>
                  <span className="font-mono font-semibold">{scope.id}</span>
                  <span className="text-[10px] opacity-50">{timeAgo(scope.timestamp)}</span>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteRecentScope(scope.type, scope.id); }}
                  className="absolute -top-1.5 -right-1.5 hidden group-hover:flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-white text-[8px] shadow-sm hover:scale-110 transition-transform"
                  aria-label="Remove from recents"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cloud Provider Selector */}
      <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
          Cloud Provider
        </h3>
        <div className="flex gap-3">
          <button
            onClick={() => setCloudProvider("gcp")}
            disabled={isRunning}
            className={`flex-1 flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-150 ${
              cloudProvider === "gcp"
                ? "ring-2 ring-blue-500/40 border-blue-400/60 dark:border-blue-400/30 bg-blue-50/50 dark:bg-blue-500/[0.06]"
                : "border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] hover:border-gray-300 dark:hover:border-white/[0.1]"
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center">
              <GCPLogo className="h-5 w-5" />
            </div>
            <div className="text-left">
              <p className={`text-sm font-medium ${cloudProvider === "gcp" ? "text-blue-700 dark:text-blue-300" : "text-gray-700 dark:text-gray-200"}`}>Google Cloud</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">GCP resources via ADC</p>
            </div>
          </button>
          <button
            onClick={() => setCloudProvider("aws")}
            disabled={isRunning}
            className={`flex-1 flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-150 ${
              cloudProvider === "aws"
                ? "ring-2 ring-orange-500/40 border-orange-400/60 dark:border-orange-400/30 bg-orange-50/50 dark:bg-orange-500/[0.06]"
                : "border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] hover:border-gray-300 dark:hover:border-white/[0.1]"
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-500/20 flex items-center justify-center">
              <AWSLogo className="h-5 w-5" />
            </div>
            <div className="text-left">
              <p className={`text-sm font-medium ${cloudProvider === "aws" ? "text-orange-700 dark:text-orange-300" : "text-gray-700 dark:text-gray-200"}`}>Amazon Web Services</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-400">
                {awsConfigured ? "Configured" : "Not configured — set up in Settings"}
              </p>
            </div>
          </button>
        </div>
        {cloudProvider === "aws" && !awsConfigured && (
          <div className="mt-3 flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>AWS credentials required.</span>
            <a href="/settings" className="text-primary hover:underline">Configure in Settings →</a>
          </div>
        )}
      </div>

      {/* Scope Selection */}
      <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-6 space-y-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Discovery Scope
        </h3>

        {/* Discovery Mode Selector (GCP only) */}
        {cloudProvider === "gcp" && <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Discovery Mode</label>
          <div className="flex gap-2">
            <button
              onClick={() => setDiscoveryMode("api")}
              disabled={isRunning}
              className={`flex-1 rounded-lg border px-4 py-3 text-left transition-all duration-150 ${
                discoveryMode === "api"
                  ? "border-indigo-300 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10"
                  : "border-gray-200 dark:border-white/[0.06] hover:border-gray-300 dark:hover:border-white/[0.1]"
              }`}
            >
              <p className={`text-sm font-medium ${discoveryMode === "api" ? "text-indigo-700 dark:text-indigo-300" : "text-gray-700 dark:text-gray-200"}`}>
                API Discovery
              </p>
              <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
                Fast, parallel — uses GCP Python SDKs directly
              </p>
            </button>
            <button
              onClick={() => setDiscoveryMode("bulk_export")}
              disabled={isRunning || bulkExportAvailable === false}
              className={`flex-1 rounded-lg border px-4 py-3 text-left transition-all duration-150 ${
                discoveryMode === "bulk_export"
                  ? "border-indigo-300 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10"
                  : "border-gray-200 dark:border-white/[0.06] hover:border-gray-300 dark:hover:border-white/[0.1]"
              } ${bulkExportAvailable === false ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <p className={`text-sm font-medium ${discoveryMode === "bulk_export" ? "text-indigo-700 dark:text-indigo-300" : "text-gray-700 dark:text-gray-200"}`}>
                Bulk Export
                {bulkExportAvailable === false && <span className="text-[10px] text-red-500 ml-2">(gcloud not available)</span>}
              </p>
              <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
                Precise — extracts all attributes via Cloud Asset API
              </p>
            </button>
          </div>
        </div>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {cloudProvider === "gcp" ? (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Scope Type</label>
                <select
                  value={scopeType}
                  onChange={(e) => setScopeType(e.target.value as ScopeType)}
                  className="w-full rounded-lg border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.03] px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none transition-all"
                  disabled={isRunning}
                >
                  <option value="project">Project</option>
                  <option value="folder">Folder</option>
                  <option value="organization">Organization</option>
                </select>
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                  {scopeType === "project" ? "Project ID" : scopeType === "folder" ? "Folder ID" : "Organization ID"}
                </label>
                <input
                  type="text"
                  value={scopeId}
                  onChange={(e) => setScopeId(e.target.value)}
                  placeholder={scopeType === "project" ? "my-gcp-project" : "123456789"}
                  className="w-full rounded-lg border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.03] px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none transition-all"
                  disabled={isRunning}
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Scope</label>
                <div className="w-full rounded-lg border border-gray-200 dark:border-white/[0.08] bg-gray-50 dark:bg-white/[0.02] px-3 py-2.5 text-sm text-gray-600 dark:text-gray-300">
                  Account
                </div>
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">
                  AWS Region
                </label>
                <p className="text-xs text-muted-foreground mt-1">
                  Uses the region configured in Settings. Discovery will scan all resources in that region.
                </p>
              </div>
            </>
          )}
        </div>

        {/* Cloud Asset API Status (GCP Bulk Export mode only) */}
        {cloudProvider === "gcp" && discoveryMode === "bulk_export" && scopeId.trim() && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${
            apiCheck.status === "checking"
              ? "bg-gray-50 dark:bg-white/[0.02] text-gray-500 dark:text-gray-400"
              : apiCheck.status === "done" && apiCheck.enabled
              ? "bg-green-50 dark:bg-green-500/5 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-500/20"
              : apiCheck.status === "done" && !apiCheck.enabled
              ? "bg-red-50 dark:bg-red-500/5 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-500/20"
              : ""
          }`}>
            {apiCheck.status === "checking" && (
              <><Loader2 className="h-3 w-3 animate-spin" /> Checking Cloud Asset API...</>
            )}
            {apiCheck.status === "done" && apiCheck.enabled && (
              <><CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> {apiCheck.message}</>
            )}
            {apiCheck.status === "done" && !apiCheck.enabled && (
              <><AlertCircle className="h-3.5 w-3.5 text-red-500" /> {apiCheck.message}</>
            )}
          </div>
        )}

        {/* Resource Types — GCP Categorized Selector */}
        {cloudProvider === "gcp" && (
          <ResourceTypeSelector
            selectedTypes={selectedTypes}
            onChange={setSelectedTypes}
            disabled={isRunning}
          />
        )}

        {/* Resource Types — AWS Categorized Selector */}
        {cloudProvider === "aws" && (
          <AWSResourceTypeSelector
            selectedTypes={awsResourceTypes}
            onChange={setAwsResourceTypes}
            disabled={isRunning}
          />
        )}

        {/* Start Button */}
        <button
          onClick={startDiscovery}
          disabled={isRunning || (cloudProvider === "gcp" && selectedTypes.length === 0) || (cloudProvider === "aws" && (!awsConfigured || awsResourceTypes.length === 0))}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-b from-indigo-500 to-indigo-600 text-white text-sm font-medium shadow-[0_1px_2px_rgba(0,0,0,0.1),inset_0_1px_0_rgba(255,255,255,0.1)] hover:from-indigo-400 hover:to-indigo-500 active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none"
        >
          {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {isRunning ? "Discovering..." : "Start Discovery"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-rose-200/60 dark:border-rose-500/20 bg-rose-50 dark:bg-rose-500/5 p-4 flex items-center gap-3 animate-slide-up">
          <AlertCircle className="h-4 w-4 text-rose-500 flex-shrink-0" />
          <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>
        </div>
      )}

      {/* Progress — refined */}
      {isRunning && status && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-6 animate-slide-up">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Scanning in progress...
            </p>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>{status.progress.message}</span>
              <span className="font-mono">{status.progress.completed}/{status.progress.total}</span>
            </div>
            {/* Progress bar */}
            <div className="h-1.5 rounded-full bg-gray-100 dark:bg-white/[0.04] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500 ease-out"
                style={{ width: `${status.progress.total > 0 ? (status.progress.completed / status.progress.total) * 100 : 0}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Resources found: <span className="font-semibold text-gray-900 dark:text-white">{status.resources_found}</span>
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-6 space-y-5 animate-slide-up">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 dark:bg-emerald-500/10">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Discovery Complete</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">{result.resources.length} resources found</p>
            </div>
          </div>

          {/* Summary Grid */}
          <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-7 gap-2 stagger-children">
            {Object.entries(result.summary)
              .filter(([, count]) => (count as number) > 0)
              .map(([type, count]) => (
              <div key={type} className="rounded-lg border border-gray-200/60 dark:border-white/[0.06] bg-gray-50 dark:bg-white/[0.02] p-2.5 text-center transition-all duration-150 hover:border-indigo-200 dark:hover:border-indigo-500/20 hover:shadow-sm">
                <p className="text-xl font-semibold tracking-tight text-indigo-600 dark:text-indigo-400">{count as number}</p>
                <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">{type.replace(/_/g, " ")}</p>
              </div>
            ))}
          </div>

          {/* Resource Table */}
          <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 dark:border-white/[0.04] bg-gray-50/50 dark:bg-white/[0.02]">
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Name</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Type</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Project</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Location</th>
                </tr>
              </thead>
              <tbody>
                {result.resources.slice(0, 50).map((r) => (
                  <tr key={r.id} className="border-b border-gray-100 dark:border-white/[0.04] last:border-0 hover:bg-gray-50 dark:hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-2.5 font-mono text-xs font-medium text-gray-900 dark:text-gray-100">{r.name}</td>
                    <td className="px-4 py-2.5">
                      <span className="rounded-md bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 px-2 py-0.5 text-[10px] font-medium">
                        {r.terraform_resource_type}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-500 dark:text-gray-400">{r.project}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-500 dark:text-gray-400">{r.location}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {result.resources.length > 50 && (
              <p className="px-4 py-2.5 text-xs text-gray-400 dark:text-gray-500 border-t border-gray-100 dark:border-white/[0.04]">
                Showing 50 of {result.resources.length} resources
              </p>
            )}
          </div>

          {/* Generate Button */}
          <a
            href={`/generate?job_id=${jobId}`}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-b from-indigo-500 to-indigo-600 text-white text-sm font-medium shadow-[0_1px_2px_rgba(0,0,0,0.1),inset_0_1px_0_rgba(255,255,255,0.1)] hover:from-indigo-400 hover:to-indigo-500 active:scale-[0.98] transition-all duration-150"
          >
            <Sparkles className="h-4 w-4" />
            Generate Terraform Code
            <ArrowRight className="h-4 w-4 ml-1" />
          </a>
        </div>
      )}

      {/* Bulk Export Results */}
      {bulkResult && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-6 space-y-4 animate-slide-up">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            <div>
              <h3 className="text-sm font-semibold">Bulk Export Complete</h3>
              <p className="text-xs text-muted-foreground">
                {bulkResult.resources?.length || 0} resources exported across {Object.keys(bulkResult.tf_files || {}).length} files
              </p>
            </div>
          </div>

          {/* Files generated */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Generated Terraform Files
            </h4>
            {Object.entries(bulkResult.tf_files || {}).map(([filename, content]) => (
              <div key={filename} className="rounded-lg border overflow-hidden">
                <div className="px-3 py-1.5 bg-gray-50 dark:bg-white/[0.03] border-b flex items-center justify-between">
                  <span className="text-xs font-mono text-gray-600 dark:text-gray-300">{filename}</span>
                  <button
                    onClick={() => { navigator.clipboard.writeText(content as string); }}
                    className="text-[10px] text-primary hover:underline"
                  >
                    Copy
                  </button>
                </div>
                <pre className="p-3 text-xs font-mono overflow-x-auto bg-gray-50/50 dark:bg-white/[0.01] max-h-48 overflow-y-auto">
                  <code>{(content as string).slice(0, 2000)}{(content as string).length > 2000 ? "\n..." : ""}</code>
                </pre>
              </div>
            ))}
          </div>

          <p className="text-xs text-muted-foreground">
            This code was generated directly by GCP Cloud Asset API — it reflects the exact current state of your infrastructure.
            You can copy it and run <code className="bg-gray-100 dark:bg-white/[0.05] px-1 rounded">terraform plan</code> to verify zero drift.
          </p>
        </div>
      )}
    </div>
  );
}
