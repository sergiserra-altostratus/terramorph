"use client";

import { useEffect, useState } from "react";
import {
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Play,
  FileText,
  BrainCircuit,
  Database,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface Prerequisites {
  ai_configured: boolean;
  ai_provider: string | null;
  ready: boolean;
  missing: string[];
}

export default function DriftPage() {
  const [prereqs, setPrereqs] = useState<Prerequisites | null>(null);
  const [bucket, setBucket] = useState("");
  const [prefix, setPrefix] = useState("terraform/state");
  const [projectId, setProjectId] = useState("");
  const [tfContent, setTfContent] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    apiClient.getDriftPrerequisites().then(setPrereqs).catch(() => null);
  }, []);

  const startDrift = async () => {
    if (!bucket.trim() || !projectId.trim() || !tfContent.trim()) {
      setError("All fields are required: Project ID, Bucket, and Terraform code.");
      return;
    }

    setError(null);
    setRunning(true);
    setResults(null);

    // Parse tf content into files (simple: treat as main.tf)
    const tf_files: Record<string, string> = { "main.tf": tfContent };

    try {
      const job = await apiClient.startDriftDetection({
        tf_files,
        bucket: bucket.trim(),
        prefix: prefix.trim(),
        project_id: projectId.trim(),
      });
      setJobId(job.job_id);

      // Poll for status
      const pollInterval = setInterval(async () => {
        try {
          const s = await apiClient.getDriftStatus(job.job_id);
          setStatus(s);

          if (s.status === "completed" || s.status === "failed") {
            clearInterval(pollInterval);
            if (s.status === "completed") {
              const r = await apiClient.getDriftResults(job.job_id);
              setResults(r);
            } else {
              setError(s.error || "Drift detection failed");
            }
            setRunning(false);
          }
        } catch (e) {
          clearInterval(pollInterval);
          setError(e instanceof Error ? e.message : "Status check failed");
          setRunning(false);
        }
      }, 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start drift detection");
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 shadow-sm">
          <RefreshCw className="h-4 w-4 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Drift Detection & Auto-Fix</h1>
          <p className="text-sm text-muted-foreground">
            Detect and automatically correct configuration drift using AI.
          </p>
        </div>
      </div>

      {/* Prerequisites Check */}
      {prereqs && !prereqs.ready && (
        <div className="rounded-xl border border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/5 p-4 space-y-2">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                Prerequisites not met
              </p>
              <ul className="text-xs text-amber-600 dark:text-amber-400 mt-1 space-y-1">
                {prereqs.missing.map((msg, i) => (
                  <li key={i}>• {msg}</li>
                ))}
              </ul>
              <a href="/settings" className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline">
                Go to Settings →
              </a>
            </div>
          </div>
        </div>
      )}

      {prereqs?.ready && (
        <div className="rounded-xl border border-green-200 dark:border-green-500/20 bg-green-50 dark:bg-green-500/5 p-3 flex items-center gap-3">
          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
          <span className="text-xs text-green-700 dark:text-green-300">
            AI ready ({prereqs.ai_provider}) — Drift detection available
          </span>
        </div>
      )}

      {/* Configuration Form */}
      <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-6 space-y-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Configuration
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              Project ID
            </label>
            <input
              type="text"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              placeholder="my-gcp-project"
              disabled={running || !prereqs?.ready}
              className="w-full rounded-lg border bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              <Database className="inline h-3 w-3 mr-1" />
              State Bucket (GCS)
            </label>
            <input
              type="text"
              value={bucket}
              onChange={(e) => setBucket(e.target.value)}
              placeholder="my-terraform-state-bucket"
              disabled={running || !prereqs?.ready}
              className="w-full rounded-lg border bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              State Prefix
            </label>
            <input
              type="text"
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              placeholder="terraform/state/pro"
              disabled={running || !prereqs?.ready}
              className="w-full rounded-lg border bg-background px-3 py-2.5 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50"
            />
          </div>
        </div>

        {/* Terraform Code Input */}
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1.5">
            <FileText className="inline h-3 w-3 mr-1" />
            Terraform Code (paste your generated .tf content)
          </label>
          <textarea
            value={tfContent}
            onChange={(e) => setTfContent(e.target.value)}
            placeholder={'resource "google_compute_instance" "example" {\n  name         = "my-vm"\n  machine_type = "e2-medium"\n  zone         = "us-central1-a"\n  ...\n}'}
            disabled={running || !prereqs?.ready}
            rows={10}
            className="w-full rounded-lg border bg-background px-3 py-2.5 text-sm font-mono focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50 resize-y"
          />
        </div>

        {/* Start Button */}
        <button
          onClick={startDrift}
          disabled={running || !prereqs?.ready}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-b from-indigo-500 to-indigo-600 text-white text-sm font-medium shadow-sm hover:from-indigo-400 hover:to-indigo-500 active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none"
        >
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {running ? "Running..." : "Start Drift Detection"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-500/5 p-4 flex items-center gap-3 animate-slide-up">
          <XCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Progress */}
      {running && status && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 animate-slide-up">
          <div className="flex items-center gap-3 mb-3">
            <BrainCircuit className="h-4 w-4 text-violet-500 animate-pulse" />
            <h3 className="text-sm font-medium">AI is working...</h3>
          </div>
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">{status.progress?.message}</p>
            <div className="h-2 rounded-full bg-secondary overflow-hidden">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500"
                style={{
                  width: `${status.progress?.max_iterations ? (status.progress.iteration / status.progress.max_iterations) * 100 : 10}%`,
                }}
              />
            </div>
            <p className="text-[10px] text-muted-foreground">
              Iteration {status.progress?.iteration || 0} / {status.progress?.max_iterations || 10}
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {results?.result && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 space-y-4 animate-slide-up">
          <div className="flex items-center gap-3">
            {results.result.drift_fixed || !results.result.drift_detected ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-500" />
            )}
            <div>
              <h3 className="text-sm font-semibold">{results.result.message}</h3>
              {results.result.iterations_needed > 0 && (
                <p className="text-xs text-muted-foreground">
                  Completed in {results.result.iterations_needed} iteration(s)
                </p>
              )}
            </div>
          </div>

          {/* Fixed Files */}
          {results.result.final_files && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Final Terraform Code
              </h4>
              {Object.entries(results.result.final_files as Record<string, string>).map(([filename, content]) => (
                <div key={filename} className="rounded-lg border overflow-hidden">
                  <div className="px-3 py-1.5 bg-muted/30 border-b">
                    <span className="text-xs font-mono text-muted-foreground">{filename}</span>
                  </div>
                  <pre className="p-3 text-xs font-mono overflow-x-auto bg-muted/10 max-h-64 overflow-y-auto">
                    <code>{content}</code>
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
