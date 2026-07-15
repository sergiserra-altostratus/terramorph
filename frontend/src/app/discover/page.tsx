"use client";

import { useState } from "react";
import { Play, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { DiscoveryStatus, DiscoveryResult } from "@/lib/api";
import { ALL_RESOURCE_TYPES, RESOURCE_TYPE_LABELS } from "@/types";
import type { ResourceType, ScopeType } from "@/types";

export default function DiscoverPage() {
  const [scopeType, setScopeType] = useState<ScopeType>("project");
  const [scopeId, setScopeId] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<ResourceType[]>(ALL_RESOURCE_TYPES);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<DiscoveryStatus | null>(null);
  const [result, setResult] = useState<DiscoveryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const toggleResourceType = (type: ResourceType) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const startDiscovery = async () => {
    if (!scopeId.trim()) {
      setError("Please enter a scope ID");
      return;
    }
    setError(null);
    setIsRunning(true);
    setResult(null);

    try {
      const job = await apiClient.startDiscovery({
        scope: { type: scopeType, id: scopeId.trim() },
        resource_types: selectedTypes,
      });
      setJobId(job.job_id);

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
          setError(e instanceof Error ? e.message : "Status check failed");
          setIsRunning(false);
        }
      }, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start discovery");
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Discover Resources</h1>
        <p className="text-muted-foreground">
          Scan your GCP infrastructure to discover existing resources.
        </p>
      </div>

      {/* Scope Selection */}
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <h3 className="text-sm font-medium">Discovery Scope</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-muted-foreground mb-1.5">
              Scope Type
            </label>
            <select
              value={scopeType}
              onChange={(e) => setScopeType(e.target.value as ScopeType)}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              disabled={isRunning}
            >
              <option value="project">Project</option>
              <option value="folder">Folder</option>
              <option value="organization">Organization</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs text-muted-foreground mb-1.5">
              {scopeType === "project" ? "Project ID" : scopeType === "folder" ? "Folder ID" : "Organization ID"}
            </label>
            <input
              type="text"
              value={scopeId}
              onChange={(e) => setScopeId(e.target.value)}
              placeholder={scopeType === "project" ? "my-gcp-project" : "123456789"}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              disabled={isRunning}
            />
          </div>
        </div>

        {/* Resource Types */}
        <div>
          <label className="block text-xs text-muted-foreground mb-2">Resource Types</label>
          <div className="flex flex-wrap gap-2">
            {ALL_RESOURCE_TYPES.map((type) => (
              <button
                key={type}
                onClick={() => toggleResourceType(type)}
                disabled={isRunning}
                className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
                  selectedTypes.includes(type)
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-background text-muted-foreground hover:bg-accent"
                }`}
              >
                {RESOURCE_TYPE_LABELS[type]}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={startDiscovery}
          disabled={isRunning || selectedTypes.length === 0}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {isRunning ? "Discovering..." : "Start Discovery"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Progress */}
      {isRunning && status && (
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-sm font-medium mb-3">Discovery Progress</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{status.progress.message}</span>
              <span>{status.progress.completed}/{status.progress.total}</span>
            </div>
            <div className="h-2 rounded-full bg-secondary">
              <div
                className="h-2 rounded-full bg-primary transition-all duration-300"
                style={{ width: `${status.progress.total > 0 ? (status.progress.completed / status.progress.total) * 100 : 0}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Resources found: {status.resources_found}
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-500" />
            <h3 className="text-sm font-medium">
              Discovery Complete — {result.resources.length} resources found
            </h3>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {Object.entries(result.summary).map(([type, count]) => (
              <div key={type} className="rounded-md border p-3 text-center">
                <p className="text-2xl font-bold">{count as number}</p>
                <p className="text-xs text-muted-foreground">{type.replace("_", " ")}</p>
              </div>
            ))}
          </div>

          <div className="border rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2 text-left font-medium">Name</th>
                  <th className="px-4 py-2 text-left font-medium">Type</th>
                  <th className="px-4 py-2 text-left font-medium">Project</th>
                  <th className="px-4 py-2 text-left font-medium">Location</th>
                </tr>
              </thead>
              <tbody>
                {result.resources.slice(0, 50).map((r) => (
                  <tr key={r.id} className="border-b">
                    <td className="px-4 py-2 font-mono text-xs">{r.name}</td>
                    <td className="px-4 py-2">
                      <span className="rounded bg-secondary px-2 py-0.5 text-xs">
                        {r.terraform_resource_type}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{r.project}</td>
                    <td className="px-4 py-2 text-muted-foreground">{r.location}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <a
            href={`/generate?job_id=${jobId}`}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Generate Terraform Code →
          </a>
        </div>
      )}
    </div>
  );
}
