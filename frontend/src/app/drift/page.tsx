"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
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
  Circle,
  Square,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import Terminal from "@/components/Terminal";
import { useDriftWebSocket } from "@/lib/useDriftWebSocket";
import { computeDiff } from "@/lib/diff";

interface Prerequisites {
  ai_configured: boolean;
  ai_provider: string | null;
  ready: boolean;
  missing: string[];
}

const phases = [
  { key: "init", label: "Init" },
  { key: "plan", label: "Plan" },
  { key: "fix", label: "AI Fix" },
  { key: "import", label: "Import" },
  { key: "verify", label: "Verify" },
  { key: "done", label: "Done" },
];

function DriftPageContent() {
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
  const [importContent, setImportContent] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [terminalCollapsed, setTerminalCollapsed] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  // WebSocket hook for real-time streaming
  const { lines, isConnected, currentPhase, phaseMessage, isComplete, error: wsError } = useDriftWebSocket(jobId);

  useEffect(() => {
    apiClient.getDriftPrerequisites().then(setPrereqs).catch(() => null);
  }, []);

  // When WebSocket completes, fetch results
  useEffect(() => {
    if (isComplete && jobId) {
      apiClient.getDriftResults(jobId)
        .then((r) => {
          setResults(r);
          setRunning(false);
          setCancelling(false);
        })
        .catch((e) => {
          // Job might have been cancelled
          setRunning(false);
          setCancelling(false);
        });
    }
  }, [isComplete, jobId]);

  // Fallback: if WebSocket fails, use polling
  useEffect(() => {
    if (wsError && jobId && running) {
      const pollInterval = setInterval(async () => {
        try {
          const s = await apiClient.getDriftStatus(jobId);
          setStatus(s);
          if (s.status === "completed" || s.status === "failed" || s.status === "cancelled") {
            clearInterval(pollInterval);
            if (s.status === "completed") {
              const r = await apiClient.getDriftResults(jobId);
              setResults(r);
            } else if (s.status === "cancelled") {
              setError("Process cancelled by user.");
            } else {
              setError(s.error || "Drift detection failed");
            }
            setRunning(false);
            setCancelling(false);
          }
        } catch (e) {
          clearInterval(pollInterval);
          setError(e instanceof Error ? e.message : "Status check failed");
          setRunning(false);
          setCancelling(false);
        }
      }, 3000);
      return () => clearInterval(pollInterval);
    }
  }, [wsError, jobId, running]);

  // Filter TF content when project selection changes (multi-project scenario)
  useEffect(() => {
    if (detectedProjects.length > 1 && projectId && allGeneratedFiles.length > 0) {
      const filteredBlocks: string[] = [];
      for (const file of allGeneratedFiles) {
        const blocks = file.content.split(/(?=\nresource |^resource )/);
        for (const block of blocks) {
          const trimmed = block.trim();
          if (!trimmed) continue;
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
      apiClient.request<any>("/generations?limit=1")
        .then((data) => {
          const gen = data.generations?.[0];
          if (gen) {
            return apiClient.request<any>(`/generations/${gen.id}`);
          }
        })
        .then((genData) => {
          if (genData && genData.files) {
            const resourceFiles = genData.files.filter(
              (f: any) => f.filename.endsWith(".tf") && f.filename !== "provider.tf" && f.filename !== "backend.tf"
            );
            setAllGeneratedFiles(resourceFiles);

            // Separate import.tf from display content (user doesn't need to edit imports)
            const importFile = genData.files.find((f: any) => f.filename === "import.tf");
            const displayFiles = resourceFiles.filter((f: any) => f.filename !== "import.tf");

            const allTf = displayFiles
              .map((f: any) => `# --- ${f.filename} ---\n${f.content}`)
              .join("\n\n");
            setTfContent(allTf);

            // Store import content separately
            if (importFile) {
              setImportContent(importFile.content);
            }

            const backendFile = genData.files.find((f: any) => f.filename === "backend.tf");
            if (backendFile) {
              const bucketMatch = backendFile.content.match(/bucket\s*=\s*"([^"]+)"/);
              const prefixMatch = backendFile.content.match(/prefix\s*=\s*"([^"]+)"/);
              if (bucketMatch) setBucket(bucketMatch[1]);
              if (prefixMatch) setPrefix(prefixMatch[1]);
            }

            const projectMatches = allTf.match(/project\s*=\s*"([^"]+)"/g) || [];
            const detected = Array.from(new Set(
              projectMatches.map((m: string) => m.match(/"([^"]+)"/)?.[1]).filter(Boolean)
            )) as string[];
            if (detected.length === 1) {
              setProjectId(detected[0]);
            } else if (detected.length > 1) {
              setDetectedProjects(detected);
              setProjectId(detected[0]);
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
    setTerminalCollapsed(false);
    setCancelling(false);

    // Parse file markers (# --- filename.tf ---) into separate files
    // If no markers found, send as single main.tf
    const tf_files: Record<string, string> = {};
    const markerRegex = /^# --- (.+\.tf) ---$/;
    let currentFile: string | null = null;
    let currentLines: string[] = [];

    for (const line of tfContent.split("\n")) {
      const match = line.match(markerRegex);
      if (match) {
        // Save previous file
        if (currentFile && currentLines.length > 0) {
          tf_files[currentFile] = currentLines.join("\n").trim();
        }
        currentFile = match[1];
        currentLines = [];
      } else {
        currentLines.push(line);
      }
    }
    // Save last file
    if (currentFile && currentLines.length > 0) {
      tf_files[currentFile] = currentLines.join("\n").trim();
    }

    // If no markers were found, treat entire content as main.tf
    if (Object.keys(tf_files).length === 0) {
      tf_files["main.tf"] = tfContent.trim();
    }

    // Include import.tf if available (auto-loaded from Generate)
    if (importContent) {
      tf_files["import.tf"] = importContent;
    }

    try {
      const job = await apiClient.startDriftDetection({
        tf_files,
        bucket: bucket.trim(),
        prefix: prefix.trim(),
        project_id: projectId.trim(),
      });
      setJobId(job.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start drift detection");
      setRunning(false);
    }
  };

  const stopDrift = useCallback(async () => {
    if (!jobId) return;
    setCancelling(true);
    try {
      await apiClient.cancelDrift(jobId);
    } catch {
      // Even if the API call fails, UI shows cancelling state
    }
  }, [jobId]);

  // Has the job ever been started (show terminal area)
  const hasJob = jobId !== null;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div>
          <h1 className="text-lg font-medium">Drift Detection & Auto-Fix</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Detect and correct configuration drift using AI.
          </p>
        </div>
      </div>

      {/* Prerequisites Check */}
      {prereqs && !prereqs.ready && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium">Prerequisites not met</p>
              <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                {prereqs.missing.map((msg, i) => (
                  <li key={i}>• {msg}</li>
                ))}
              </ul>
              <a href="/settings" className="text-xs text-emerald-500 hover:underline mt-1 inline-block">
                Go to Settings →
              </a>
            </div>
          </div>
        </div>
      )}

      {prereqs?.ready && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          AI ready ({prereqs.ai_provider})
        </div>
      )}

      {/* Configuration + Code Editor + Terminal */}
      <div className={`grid grid-cols-1 gap-4 ${hasJob ? "lg:grid-cols-12" : "lg:grid-cols-12"}`}>
        {/* Left: Configuration */}
        <div className="lg:col-span-3 rounded-md border border-border bg-background p-5 space-y-4">
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

          {/* Action buttons */}
          <div className="space-y-2">
            <button
              onClick={startDrift}
              disabled={running || !prereqs?.ready}
              className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:pointer-events-none"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? "Running..." : "Start Drift Detection"}
            </button>

            {/* Stop button — only visible when running */}
            {running && (
              <button
                onClick={stopDrift}
                disabled={cancelling}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-red-400/50 text-red-400 text-sm font-medium hover:bg-red-400/10 transition-colors disabled:opacity-40"
              >
                <Square className="h-3.5 w-3.5 fill-current" />
                {cancelling ? "Stopping..." : "Stop"}
              </button>
            )}
          </div>
        </div>

        {/* Center: Code Editor */}
        <div className={`${hasJob ? "lg:col-span-3" : "lg:col-span-9"} rounded-md border border-border bg-background overflow-hidden flex flex-col transition-all duration-300`}>
          <div className="px-4 py-2.5 border-b border-border/50 flex items-center justify-between bg-muted/20">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="h-3 w-3" />
              Terraform Code
            </label>
            <span className="text-[10px] text-muted-foreground">
              {tfContent ? `${tfContent.split("\n").length} lines` : "Paste or auto-load from Generate"}
            </span>
          </div>
          <div className="flex flex-1 overflow-hidden" style={{ minHeight: "350px", maxHeight: "500px" }}>
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

        {/* Right: Terminal — visible once a job starts */}
        {hasJob && (
          <div className="lg:col-span-6 flex flex-col space-y-2 animate-slide-up">
            {/* Phase progress indicator */}
            <div className="flex items-center gap-1 flex-wrap">
              {phases.map((phase, i) => {
                const phaseIndex = phases.findIndex((p) => p.key === currentPhase);
                const isActive = phase.key === currentPhase;
                const isDone = i < phaseIndex || currentPhase === "done";

                return (
                  <div key={phase.key} className="flex items-center">
                    <div
                      className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[9px] font-medium transition-all ${
                        isActive
                          ? "bg-indigo-100 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300"
                          : isDone
                          ? "bg-green-50 dark:bg-green-500/10 text-green-600 dark:text-green-400"
                          : "bg-muted/50 text-muted-foreground"
                      }`}
                    >
                      {isActive && running && (
                        <Circle className="h-1.5 w-1.5 fill-indigo-500 animate-pulse" />
                      )}
                      {isDone && <CheckCircle2 className="h-2.5 w-2.5" />}
                      {phase.label}
                    </div>
                    {i < phases.length - 1 && (
                      <div className={`w-3 h-px mx-0.5 ${isDone ? "bg-green-300 dark:bg-green-600" : "bg-border"}`} />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Connection status */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {running && phaseMessage && (
                  <span className="inline-flex items-center gap-1.5 text-[10px] text-indigo-600 dark:text-indigo-400 font-medium">
                    <BrainCircuit className="h-3 w-3 animate-pulse" />
                    {phaseMessage}
                  </span>
                )}
                {running && !phaseMessage && (
                  <span className="inline-flex items-center gap-1 text-[10px] text-indigo-600 dark:text-indigo-400 font-medium">
                    <BrainCircuit className="h-3 w-3 animate-pulse" />
                    Starting...
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-green-500" : "bg-gray-400"}`} />
                <span className="text-[10px] text-muted-foreground">
                  {isConnected ? "Live" : wsError ? "Polling" : "..."}
                </span>
              </div>
            </div>

            {/* Terminal component */}
            <Terminal
              lines={lines}
              isActive={running}
              currentPhase={currentPhase}
              collapsed={terminalCollapsed}
              onToggleCollapse={() => setTerminalCollapsed(!terminalCollapsed)}
              maxHeight="420px"
            />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md border border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-500/5 p-4 animate-slide-up">
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

      {/* Results — Diff view */}
      {results?.result && (
        <DiffResults
          originalContent={tfContent}
          results={results}
        />
      )}
    </div>
  );
}

/** Diff results component with GitHub-style line highlighting */
function DiffResults({ originalContent, results }: { originalContent: string; results: any }) {
  const fixedContent = results.result.final_files
    ? Object.entries(results.result.final_files as Record<string, string>)
        .filter(([f]) => f !== "provider.tf" && f !== "backend.tf")
        .map(([f, c]) => `# --- ${f} ---\n${c}`)
        .join("\n\n")
    : "";

  const diff = computeDiff(originalContent, fixedContent);

  return (
    <div className="space-y-3 animate-slide-up">
      {/* Result header */}
      <div className="rounded-md border border-border bg-background p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {results.result.drift_fixed || !results.result.drift_detected ? (
            <CheckCircle2 className="h-5 w-5 text-green-500" />
          ) : (
            <AlertCircle className="h-5 w-5 text-amber-500" />
          )}
          <div>
            <span className="text-sm font-semibold">{results.result.message}</span>
            {results.result.iterations_needed > 0 && (
              <span className="text-xs text-muted-foreground ml-2">
                ({results.result.iterations_needed} iteration(s))
              </span>
            )}
          </div>
        </div>
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
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-white/[0.08] px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/[0.04] transition-colors"
          >
            <Download className="h-3 w-3" />
            Download
          </button>
        )}
      </div>

      {/* Drift not resolved */}
      {results.result.drift_detected && !results.result.drift_fixed && results.result.remaining_drift && (
        <div className="rounded-md border border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/5 p-4">
          <p className="text-xs font-semibold text-amber-800 dark:text-amber-300 mb-1.5">Unresolved Drift</p>
          <pre className="text-[10px] font-mono text-amber-700 dark:text-amber-400 whitespace-pre-wrap max-h-32 overflow-y-auto">{results.result.remaining_drift}</pre>
        </div>
      )}

      {/* Side-by-side diff */}
      {diff.hasChanges && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 rounded-md border border-border overflow-hidden">
          {/* Left: Original */}
          <div className="border-r border-border overflow-hidden flex flex-col">
            <div className="px-4 py-2.5 border-b border-border/50 bg-red-50/30 dark:bg-red-500/[0.03]">
              <span className="text-xs font-semibold text-red-700 dark:text-red-400 uppercase tracking-wider">Original</span>
            </div>
            <div className="flex-1 overflow-auto max-h-[500px] bg-white dark:bg-[#0d1117]">
              {diff.left.map((line, i) => (
                <div
                  key={i}
                  className={`flex text-xs font-mono leading-5 ${
                    line.state === "removed"
                      ? "bg-red-50/70 dark:bg-red-500/[0.07] border-l-2 border-red-400 dark:border-red-500/50"
                      : line.state === "padding"
                      ? "bg-gray-50/50 dark:bg-gray-800/20"
                      : ""
                  }`}
                >
                  <span className="w-10 flex-shrink-0 text-right pr-2 py-px text-[10px] text-gray-400 dark:text-gray-600 select-none border-r border-gray-100 dark:border-white/[0.04]">
                    {line.lineNumber || ""}
                  </span>
                  <span className={`flex-1 px-3 py-px whitespace-pre-wrap break-all ${
                    line.state === "removed" ? "text-red-800 dark:text-red-300" : "text-gray-700 dark:text-gray-300"
                  }`}>
                    {line.state === "padding" ? "\u00A0" : line.text}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Fixed */}
          <div className="overflow-hidden flex flex-col">
            <div className="px-4 py-2.5 border-b border-border/50 bg-green-50/30 dark:bg-green-500/[0.03]">
              <span className="text-xs font-semibold text-green-700 dark:text-green-400 uppercase tracking-wider">Fixed</span>
            </div>
            <div className="flex-1 overflow-auto max-h-[500px] bg-white dark:bg-[#0d1117]">
              {diff.right.map((line, i) => (
                <div
                  key={i}
                  className={`flex text-xs font-mono leading-5 ${
                    line.state === "added"
                      ? "bg-green-50/70 dark:bg-green-500/[0.07] border-l-2 border-green-400 dark:border-green-500/50"
                      : line.state === "padding"
                      ? "bg-gray-50/50 dark:bg-gray-800/20"
                      : ""
                  }`}
                >
                  <span className="w-10 flex-shrink-0 text-right pr-2 py-px text-[10px] text-gray-400 dark:text-gray-600 select-none border-r border-gray-100 dark:border-white/[0.04]">
                    {line.lineNumber || ""}
                  </span>
                  <span className={`flex-1 px-3 py-px whitespace-pre-wrap break-all ${
                    line.state === "added" ? "text-green-800 dark:text-green-300" : "text-gray-700 dark:text-gray-300"
                  }`}>
                    {line.state === "padding" ? "\u00A0" : line.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* No changes case */}
      {!diff.hasChanges && results.result.final_files && (
        <div className="rounded-md border border-green-200 dark:border-green-500/20 bg-green-50 dark:bg-green-500/5 p-6 text-center">
          <CheckCircle2 className="h-8 w-8 text-green-500 mx-auto mb-2" />
          <p className="text-sm font-medium text-green-800 dark:text-green-300">No changes needed — code matches infrastructure.</p>
        </div>
      )}
    </div>
  );
}

export default function DriftPage() {
  return (
    <Suspense fallback={<div className="animate-pulse p-8 text-muted-foreground">Loading...</div>}>
      <DriftPageContent />
    </Suspense>
  );
}
