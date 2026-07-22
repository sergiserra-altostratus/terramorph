"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
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
  Download,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface Prerequisites {
  ai_configured: boolean;
  ai_provider: string | null;
  ready: boolean;
  missing: string[];
}

export default function DriftPage() {
  const searchParams = useSearchParams();
  const fromGenerate = searchParams.get("from_generate") === "true";
  const sourceJobId = searchParams.get("job_id");

  const [prereqs, setPrereqs] = useState<Prerequisites | null>(null);
  const [bucket, setBucket] = useState("");
  const [prefix, setPrefix] = useState("terraform/state");
  const [projectId, setProjectId] = useState("");
  const [tfContent, setTfContent] = useState("");
  const [detectedProjects, setDetectedProjects] = useState<string[]>([]);
  const [allGeneratedFiles, setAllGeneratedFiles] = useState<Array<{filename: string; content: string}>>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    apiClient.getDriftPrerequisites().then(setPrereqs).catch(() => null);
  }, []);

  // Filter TF content when project selection changes (multi-project scenario)
  useEffect(() => {
    if (detectedProjects.length > 1 && projectId && allGeneratedFiles.length > 0) {
      // Filter resource blocks that belong to the selected project
      const filteredBlocks: string[] = [];
      for (const file of allGeneratedFiles) {
        // Split content into resource blocks
        const blocks = file.content.split(/(?=\nresource |^resource )/);
        for (const block of blocks) {
          const trimmed = block.trim();
          if (!trimmed) continue;
          // Include block if it contains project = "selected_project" or has no project field
          if (trimmed.includes(`project = "${projectId}"`) || !trimmed.match(/project\s*=\s*"/)) {
            filteredBlocks.push(trimmed);
          }
        }
      }
      if (filteredBlocks.length > 0) {
        setTfContent(filteredBlocks.join("\n\n"));
      }
    }
  }, [projectId, detectedProjects, allGeneratedFiles]);

  // Auto-load generated files from previous generation
  useEffect(() => {
    if (fromGenerate && sourceJobId) {
      // Try to load the latest generation for this job
      apiClient.request<any>("/generations?limit=1")
        .then((data) => {
          const gen = data.generations?.[0];
          if (gen) {
            return apiClient.request<any>(`/generations/${gen.id}`);
          }
        })
        .then((genData) => {
          if (genData && genData.files) {
            // Store all files for later filtering
            const resourceFiles = genData.files.filter(
              (f: any) => f.filename.endsWith(".tf") && f.filename !== "provider.tf" && f.filename !== "import.tf" && f.filename !== "backend.tf"
            );
            setAllGeneratedFiles(resourceFiles);

            // Concatenate all .tf files as content (exclude backend.tf and provider.tf — drift service generates these)
            const allTf = resourceFiles
              .map((f: any) => `# --- ${f.filename} ---\n${f.content}`)
              .join("\n\n");
            setTfContent(allTf);

            // Try to extract bucket/prefix from backend.tf if present
            const backendFile = genData.files.find((f: any) => f.filename === "backend.tf");
            if (backendFile) {
              const bucketMatch = backendFile.content.match(/bucket\s*=\s*"([^"]+)"/);
              const prefixMatch = backendFile.content.match(/prefix\s*=\s*"([^"]+)"/);
              if (bucketMatch) setBucket(bucketMatch[1]);
              if (prefixMatch) setPrefix(prefixMatch[1]);
            }

            // Auto-detect projects from resource blocks
            const projectMatches = allTf.match(/project\s*=\s*"([^"]+)"/g) || [];
            const detectedProjects = [...new Set(
              projectMatches.map((m: string) => m.match(/"([^"]+)"/)?.[1]).filter(Boolean)
            )] as string[];
            if (detectedProjects.length === 1) {
              setProjectId(detectedProjects[0]);
            } else if (detectedProjects.length > 1) {
              setDetectedProjects(detectedProjects);
              setProjectId(detectedProjects[0]);
            }
          }
        })
        .catch(() => {});
    }
  }, [fromGenerate, sourceJobId]);

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

      {/* Configuration + Code Editor — Side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Configuration */}
        <div className="lg:col-span-4 rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Configuration
            </h3>
            {fromGenerate && tfContent && (
              <span className="inline-flex items-center rounded-md bg-indigo-50 dark:bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-600 dark:text-indigo-400">
                ✓ Auto-loaded
              </span>
            )}
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                Project ID
                {detectedProjects.length > 1 && (
                  <span className="ml-1 text-[10px] text-primary">({detectedProjects.length} detected)</span>
                )}
              </label>
              {detectedProjects.length > 1 ? (
                <select
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  disabled={running || !prereqs?.ready}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50"
                >
                  {detectedProjects.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              ) : (
                <input
                  type="text" value={projectId} onChange={(e) => setProjectId(e.target.value)}
                  placeholder="my-gcp-project" disabled={running || !prereqs?.ready}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50"
                />
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                <Database className="inline h-3 w-3 mr-1" />
                State Bucket (GCS)
              </label>
              <input
                type="text" value={bucket} onChange={(e) => setBucket(e.target.value)}
                placeholder="my-terraform-state-bucket" disabled={running || !prereqs?.ready}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">State Prefix</label>
              <input
                type="text" value={prefix} onChange={(e) => setPrefix(e.target.value)}
                placeholder="terraform/state/pro" disabled={running || !prereqs?.ready}
                className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all disabled:opacity-50"
              />
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={startDrift}
            disabled={running || !prereqs?.ready}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-b from-indigo-500 to-indigo-600 text-white text-sm font-medium shadow-sm hover:from-indigo-400 hover:to-indigo-500 active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none"
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {running ? "Running..." : "Start Drift Detection"}
          </button>
        </div>

        {/* Right: Code Editor */}
        <div className="lg:col-span-8 rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] overflow-hidden flex flex-col">
          <div className="px-4 py-2.5 border-b border-border/50 flex items-center justify-between bg-muted/20">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="h-3 w-3" />
              Terraform Code
            </label>
            <span className="text-[10px] text-muted-foreground">
              {tfContent ? `${tfContent.split("\n").length} lines` : "Paste or auto-load from Generate"}
            </span>
          </div>
          <div className="flex flex-1 overflow-hidden" style={{ minHeight: "300px", maxHeight: "500px" }}>
            {/* Line numbers */}
            <div className="flex-shrink-0 w-10 bg-muted/30 border-r border-border/50 py-2.5 select-none overflow-hidden">
              <div className="text-[10px] font-mono text-muted-foreground text-right pr-2 leading-[1.65rem]">
                {tfContent.split("\n").map((_, i) => (
                  <div key={i}>{i + 1}</div>
                ))}
                {!tfContent && <div>1</div>}
              </div>
            </div>
            {/* Code input */}
            <textarea
              value={tfContent}
              onChange={(e) => setTfContent(e.target.value)}
              placeholder={'resource "google_compute_instance" "example" {\n  name         = "my-vm"\n  machine_type = "e2-medium"\n  zone         = "us-central1-a"\n}'}
              disabled={running || !prereqs?.ready}
              spellCheck={false}
              className="flex-1 w-full py-2.5 px-3 text-sm font-mono bg-transparent outline-none disabled:opacity-50 resize-none leading-[1.65rem] overflow-auto"
            />
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-500/5 p-4 animate-slide-up">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">Drift Detection Error</p>
              <div className="mt-2 rounded-lg bg-red-100/50 dark:bg-red-900/20 p-3 overflow-x-auto">
                <pre className="text-xs font-mono text-red-700 dark:text-red-300 whitespace-pre-wrap break-words">{error}</pre>
              </div>
              {error.includes("permission") && (
                <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                  💡 Tip: Ensure the service account has the required IAM roles for this project.
                </p>
              )}
              {error.includes("bucket") && (
                <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                  💡 Tip: Verify the bucket exists and you have access to it.
                </p>
              )}
            </div>
          </div>
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

      {/* Results — Side by side layout */}
      {results?.result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-slide-up">
          {/* Left: Original code (input) */}
          <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-border/50 flex items-center justify-between bg-muted/20">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Original Code</span>
              <span className="text-[10px] text-muted-foreground">{tfContent.split("\n").length} lines</span>
            </div>
            <pre className="flex-1 p-4 text-xs font-mono overflow-auto max-h-[500px] bg-muted/5">
              <code>{tfContent}</code>
            </pre>
          </div>

          {/* Right: Results + Fixed code */}
          <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-border/50 flex items-center justify-between bg-muted/20">
              <div className="flex items-center gap-3">
                {results.result.drift_fixed || !results.result.drift_detected ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                )}
                <div>
                  <span className="text-xs font-semibold">{results.result.message}</span>
                  {results.result.iterations_needed > 0 && (
                    <span className="text-[10px] text-muted-foreground ml-2">
                      ({results.result.iterations_needed} iteration(s))
                    </span>
                  )}
                </div>
              </div>
              {/* Download button */}
              {results.result.final_files && (
                <button
                  onClick={() => {
                    const allContent = Object.entries(results.result.final_files as Record<string, string>)
                      .map(([f, c]) => `# --- ${f} ---\n${c}`).join("\n\n");
                    const blob = new Blob([allContent], { type: "text/plain" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a"); a.href = url; a.download = "drift-fixed.tf"; a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-white/[0.08] px-2.5 py-1.5 text-[10px] font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/[0.04] transition-colors"
                >
                  <Download className="h-3 w-3" />
                  Download
                </button>
              )}
            </div>

            {/* Drift not resolved summary */}
            {results.result.drift_detected && !results.result.drift_fixed && results.result.remaining_drift && (
              <div className="px-4 py-3 bg-amber-50/50 dark:bg-amber-500/5 border-b border-amber-200/50 dark:border-amber-500/10">
                <p className="text-xs font-semibold text-amber-800 dark:text-amber-300 mb-1.5">Unresolved Drift Summary</p>
                <pre className="text-[10px] font-mono text-amber-700 dark:text-amber-400 whitespace-pre-wrap max-h-32 overflow-y-auto">{results.result.remaining_drift}</pre>
              </div>
            )}

            {/* Fixed Files */}
            {results.result.final_files ? (
              <div className="flex-1 overflow-auto max-h-[500px]">
                {Object.entries(results.result.final_files as Record<string, string>).map(([filename, content]) => (
                  <div key={filename}>
                    <div className="px-4 py-1.5 bg-green-50/50 dark:bg-green-500/5 border-b border-border/30 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-green-700 dark:text-green-400">{filename}</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(content)}
                        className="text-[10px] text-primary hover:underline"
                      >
                        Copy
                      </button>
                    </div>
                    <pre className="p-4 text-xs font-mono overflow-x-auto border-b border-border/20">
                      <code>{content}</code>
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center p-8">
                <p className="text-sm text-muted-foreground">No corrected files available</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
