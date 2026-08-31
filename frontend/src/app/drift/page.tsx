"use client";

import { Suspense, useEffect, useState, useCallback, useRef } from "react";
import { useSearchParams } from "next/navigation";
import {
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
  Upload,
  Trash2,
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

  // Shared state
  const [prereqs, setPrereqs] = useState<Prerequisites | null>(null);
  const [projectId, setProjectId] = useState("");
  const [bucket, setBucket] = useState("");
  const [prefix, setPrefix] = useState("terraform/state");
  const [detectedProjects, setDetectedProjects] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [terminalCollapsed, setTerminalCollapsed] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  // Mode: "generate" (auto-loaded) or "upload" (drag & drop)
  const mode = fromGenerate ? "generate" : "upload";

  // Generate mode state
  const [tfContent, setTfContent] = useState("");
  const [importContent, setImportContent] = useState<string | null>(null);

  // Upload mode state
  const [files, setFiles] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const hasBackendTf = Object.keys(files).some((f) => f.toLowerCase() === "backend.tf");

  // Original content for diff (works in both modes)
  const originalContent = mode === "generate"
    ? tfContent
    : Object.entries(files)
        .filter(([f]) => !["backend.tf", "provider.tf", "import.tf"].includes(f))
        .map(([f, c]) => `# --- ${f} ---\n${c}`)
        .join("\n\n");

  // WebSocket hook
  const { lines, isConnected, currentPhase, phaseMessage, isComplete, error: wsError } = useDriftWebSocket(jobId);

  useEffect(() => {
    apiClient.getDriftPrerequisites().then(setPrereqs).catch(() => null);
  }, []);

  // WebSocket completion
  useEffect(() => {
    if (isComplete && jobId) {
      apiClient.getDriftResults(jobId)
        .then((r) => { setResults(r); setRunning(false); setCancelling(false); })
        .catch(() => { setRunning(false); setCancelling(false); });
    }
  }, [isComplete, jobId]);

  // Polling fallback
  useEffect(() => {
    if (wsError && jobId && running) {
      const pollInterval = setInterval(async () => {
        try {
          const s = await apiClient.getDriftStatus(jobId);
          setStatus(s);
          if (s.status === "completed" || s.status === "failed" || s.status === "cancelled") {
            clearInterval(pollInterval);
            if (s.status === "completed") { const r = await apiClient.getDriftResults(jobId); setResults(r); }
            else if (s.status === "cancelled") { setError("Process cancelled by user."); }
            else { setError(s.error || "Drift detection failed"); }
            setRunning(false); setCancelling(false);
          }
        } catch (e) {
          clearInterval(pollInterval);
          setError(e instanceof Error ? e.message : "Status check failed");
          setRunning(false); setCancelling(false);
        }
      }, 3000);
      return () => clearInterval(pollInterval);
    }
  }, [wsError, jobId, running]);

  // Auto-load from Generate
  useEffect(() => {
    if (fromGenerate && sourceJobId) {
      apiClient.request<any>("/generations?limit=1")
        .then((data) => {
          const gen = data.generations?.[0];
          if (gen) return apiClient.request<any>(`/generations/${gen.id}`);
        })
        .then((genData) => {
          if (genData && genData.files) {
            const resourceFiles = genData.files.filter(
              (f: any) => f.filename.endsWith(".tf") && f.filename !== "provider.tf" && f.filename !== "backend.tf"
            );
            const importFile = genData.files.find((f: any) => f.filename === "import.tf");
            const displayFiles = resourceFiles.filter((f: any) => f.filename !== "import.tf");

            setTfContent(displayFiles.map((f: any) => `# --- ${f.filename} ---\n${f.content}`).join("\n\n"));
            if (importFile) setImportContent(importFile.content);

            const backendFile = genData.files.find((f: any) => f.filename === "backend.tf");
            if (backendFile) {
              const bm = backendFile.content.match(/bucket\s*=\s*"([^"]+)"/);
              const pm = backendFile.content.match(/prefix\s*=\s*"([^"]+)"/);
              if (bm) setBucket(bm[1]);
              if (pm) setPrefix(pm[1]);
            }

            const allTf = displayFiles.map((f: any) => f.content).join("\n");
            const projectMatches = allTf.match(/project\s*=\s*"([^"]+)"/g) || [];
            const detected = Array.from(new Set(
              projectMatches.map((m: string) => m.match(/"([^"]+)"/)?.[1]).filter(Boolean)
            )) as string[];
            if (detected.length === 1) setProjectId(detected[0]);
            else if (detected.length > 1) { setDetectedProjects(detected); setProjectId(detected[0]); }
          }
        })
        .catch(() => {});
    }
  }, [fromGenerate, sourceJobId]);

  // File upload handlers
  const processFiles = (fileList: FileList | File[]) => {
    const newFiles: Record<string, string> = { ...files };
    Array.from(fileList).forEach((file) => {
      if (file.name.endsWith(".tf") || file.name.endsWith(".tf.json")) {
        const reader = new FileReader();
        reader.onload = (e) => {
          newFiles[file.name] = e.target?.result as string;
          setFiles({ ...newFiles });

          // Auto-extract bucket/prefix/project from uploaded files
          if (file.name.toLowerCase() === "backend.tf") {
            const content = e.target?.result as string;
            const bm = content.match(/bucket\s*=\s*"([^"]+)"/);
            const pm = content.match(/prefix\s*=\s*"([^"]+)"/);
            if (bm) setBucket(bm[1]);
            if (pm) setPrefix(pm[1]);
          }
          // Auto-detect project ID from resource files
          const content = e.target?.result as string;
          const pm = content.match(/project\s*=\s*"([^"]+)"/);
          if (pm && !projectId) setProjectId(pm[1]);
        };
        reader.readAsText(file);
      }
    });
  };

  const removeFile = (filename: string) => {
    const updated = { ...files };
    delete updated[filename];
    setFiles(updated);
  };

  // Start drift detection
  const startDrift = async () => {
    setError(null);

    // Build tf_files based on mode
    let tf_files: Record<string, string> = {};

    if (mode === "upload") {
      if (!hasBackendTf) {
        setError("backend.tf is required. Please upload your backend configuration file.");
        return;
      }
      if (Object.keys(files).length < 2) {
        setError("Upload at least one resource .tf file in addition to backend.tf.");
        return;
      }
      tf_files = { ...files };
    } else {
      // Generate mode
      if (!bucket.trim() || !projectId.trim() || !tfContent.trim()) {
        setError("All fields are required: Project ID, Bucket, and Terraform code.");
        return;
      }
      // Parse markers into separate files
      const markerRegex = /^# --- (.+\.tf) ---$/;
      let currentFile: string | null = null;
      let currentLines: string[] = [];
      for (const line of tfContent.split("\n")) {
        const match = line.match(markerRegex);
        if (match) {
          if (currentFile && currentLines.length > 0) tf_files[currentFile] = currentLines.join("\n").trim();
          currentFile = match[1]; currentLines = [];
        } else { currentLines.push(line); }
      }
      if (currentFile && currentLines.length > 0) tf_files[currentFile] = currentLines.join("\n").trim();
      if (Object.keys(tf_files).length === 0) tf_files["main.tf"] = tfContent.trim();
      if (importContent) tf_files["import.tf"] = importContent;
    }

    setRunning(true); setResults(null); setTerminalCollapsed(false); setCancelling(false);

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
    try { await apiClient.cancelDrift(jobId); } catch {}
  }, [jobId]);

  const hasJob = jobId !== null;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div>
          <h1 className="text-lg font-medium">Drift Detection & Auto-Fix</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {mode === "generate"
              ? "Detect and correct drift on generated Terraform code."
              : "Upload your Terraform files to detect and fix configuration drift."}
          </p>
        </div>
      </div>

      {/* Prerequisites */}
      {prereqs && !prereqs.ready && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium">Prerequisites not met</p>
              <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                {prereqs.missing.map((msg, i) => (<li key={i}>• {msg}</li>))}
              </ul>
              <a href="/settings" className="text-xs text-emerald-500 hover:underline mt-1 inline-block">Go to Settings →</a>
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

      {/* Main layout */}
      <div className={`grid grid-cols-1 gap-4 ${hasJob ? "lg:grid-cols-12" : "lg:grid-cols-12"}`}>
        {/* Left: Configuration */}
        <div className="lg:col-span-3 space-y-4">
          {/* Config panel */}
          <div className="rounded-md border border-border bg-background p-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Configuration</h3>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Project ID</label>
              {detectedProjects.length > 1 ? (
                <select value={projectId} onChange={(e) => setProjectId(e.target.value)} disabled={running}
                  className="w-full rounded-md border bg-background px-3 py-1.5 text-sm outline-none disabled:opacity-50">
                  {detectedProjects.map((p) => (<option key={p} value={p}>{p}</option>))}
                </select>
              ) : (
                <input type="text" value={projectId} onChange={(e) => setProjectId(e.target.value)}
                  placeholder="my-gcp-project" disabled={running}
                  className="w-full rounded-md border bg-background px-3 py-1.5 text-sm outline-none disabled:opacity-50" />
              )}
            </div>

            {/* Only show bucket/prefix fields if NOT using uploaded backend.tf */}
            {mode === "generate" && (
              <>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">State Bucket (GCS)</label>
                  <input type="text" value={bucket} onChange={(e) => setBucket(e.target.value)}
                    placeholder="my-terraform-state-bucket" disabled={running}
                    className="w-full rounded-md border bg-background px-3 py-1.5 text-sm outline-none disabled:opacity-50" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">State Prefix</label>
                  <input type="text" value={prefix} onChange={(e) => setPrefix(e.target.value)}
                    placeholder="terraform/state" disabled={running}
                    className="w-full rounded-md border bg-background px-3 py-1.5 text-sm outline-none disabled:opacity-50" />
                </div>
              </>
            )}

            {mode === "upload" && bucket && (
              <div className="text-xs text-muted-foreground">
                <span className="font-medium">State:</span> <span className="font-mono">{bucket}/{prefix}</span>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="space-y-2">
            <button onClick={startDrift}
              disabled={running || !prereqs?.ready || (mode === "upload" && (!hasBackendTf || Object.keys(files).length < 2))}
              className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:pointer-events-none">
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? "Running..." : "Start Drift Detection"}
            </button>
            {running && (
              <button onClick={stopDrift} disabled={cancelling}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md border border-red-400/50 text-red-400 text-sm font-medium hover:bg-red-400/10 transition-colors disabled:opacity-40">
                <Square className="h-3.5 w-3.5 fill-current" />
                {cancelling ? "Stopping..." : "Stop"}
              </button>
            )}
          </div>
        </div>

        {/* Center: Code or Upload zone */}
        <div className={`${hasJob ? "lg:col-span-3" : "lg:col-span-9"} flex flex-col gap-3 transition-all duration-300`}>

          {/* === UPLOAD MODE === */}
          {mode === "upload" && (
            <>
              {/* Drop zone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => { e.preventDefault(); setDragOver(false); processFiles(e.dataTransfer.files); }}
                onClick={() => fileInputRef.current?.click()}
                className={`rounded-md border-2 border-dashed p-6 text-center cursor-pointer transition-all ${
                  dragOver ? "border-emerald-500 bg-emerald-500/5" : "border-border hover:border-emerald-500/30"
                } ${running ? "opacity-50 pointer-events-none" : ""}`}
              >
                <Upload className={`h-6 w-6 mx-auto mb-2 ${dragOver ? "text-emerald-500" : "text-muted-foreground"}`} />
                <p className="text-xs font-medium">Drop .tf files here or click to browse</p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  <span className="font-semibold text-amber-500">backend.tf</span> is required
                </p>
                <input ref={fileInputRef} type="file" multiple accept=".tf,.tf.json"
                  onChange={(e) => e.target.files && processFiles(e.target.files)} className="hidden" />
              </div>

              {/* File list */}
              {Object.keys(files).length > 0 && (
                <div className="rounded-md border border-border overflow-hidden">
                  <div className="px-3 py-2 border-b border-border bg-muted/20">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Files ({Object.keys(files).length})
                    </span>
                  </div>
                  <div className="p-1.5 space-y-0.5 max-h-48 overflow-y-auto">
                    {Object.keys(files).map((name) => (
                      <div key={name} className="flex items-center justify-between px-2 py-1 rounded hover:bg-muted/30">
                        <div className="flex items-center gap-2">
                          <FileText className="h-3 w-3 text-muted-foreground" />
                          <span className="text-xs font-mono">{name}</span>
                          {name.toLowerCase() === "backend.tf" && (
                            <span className="text-[9px] bg-emerald-500/10 text-emerald-500 px-1 py-0.5 rounded font-medium">required</span>
                          )}
                        </div>
                        <button onClick={() => removeFile(name)} disabled={running}
                          className="p-0.5 hover:text-red-500 text-muted-foreground transition-colors disabled:opacity-50">
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* backend.tf warning */}
              {Object.keys(files).length > 0 && !hasBackendTf && (
                <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground">backend.tf is missing.</span> This file is required to configure the remote state for drift detection.
                  </p>
                </div>
              )}
            </>
          )}

          {/* === GENERATE MODE (auto-loaded code view) === */}
          {mode === "generate" && (
            <div className="rounded-md border border-border bg-background overflow-hidden flex flex-col" style={{ minHeight: "300px", maxHeight: hasJob ? "350px" : "500px" }}>
              <div className="px-3 py-2 border-b border-border bg-muted/20 flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="h-3 w-3" /> Terraform Code
                </span>
                <span className="text-[10px] text-muted-foreground">
                  {tfContent ? `${tfContent.split("\n").length} lines · Auto-loaded` : "Loading..."}
                </span>
              </div>
              <div className="flex flex-1 overflow-hidden">
                <div className="flex-shrink-0 w-8 bg-muted/30 border-r border-border py-2 select-none overflow-hidden">
                  <div className="text-[10px] font-mono text-muted-foreground text-right pr-1.5 leading-[1.65rem]">
                    {tfContent.split("\n").map((_, i) => (<div key={i}>{i + 1}</div>))}
                    {!tfContent && <div>1</div>}
                  </div>
                </div>
                <textarea value={tfContent} onChange={(e) => setTfContent(e.target.value)}
                  disabled={running} spellCheck={false}
                  className="flex-1 w-full py-2 px-3 text-xs font-mono bg-transparent outline-none disabled:opacity-50 resize-none leading-[1.65rem] overflow-auto" />
              </div>
            </div>
          )}
        </div>

        {/* Right: Terminal */}
        {hasJob && (
          <div className="lg:col-span-6 flex flex-col space-y-2 animate-slide-up">
            {/* Phase indicator */}
            <div className="flex items-center gap-1 flex-wrap">
              {phases.map((phase, i) => {
                const phaseIndex = phases.findIndex((p) => p.key === currentPhase);
                const isActive = phase.key === currentPhase;
                const isDone = i < phaseIndex || currentPhase === "done";
                return (
                  <div key={phase.key} className="flex items-center">
                    <div className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[9px] font-medium transition-all ${
                      isActive ? "bg-muted text-foreground" : isDone ? "bg-emerald-500/10 text-emerald-500" : "bg-muted/50 text-muted-foreground"}`}>
                      {isActive && running && <Circle className="h-1.5 w-1.5 fill-emerald-400 animate-pulse" />}
                      {isDone && <CheckCircle2 className="h-2.5 w-2.5" />}
                      {phase.label}
                    </div>
                    {i < phases.length - 1 && <div className={`w-3 h-px mx-0.5 ${isDone ? "bg-emerald-500/50" : "bg-border"}`} />}
                  </div>
                );
              })}
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {running && phaseMessage && (
                  <span className="inline-flex items-center gap-1.5 text-[10px] text-emerald-500 font-medium">
                    <BrainCircuit className="h-3 w-3 animate-pulse" />{phaseMessage}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-emerald-500" : "bg-zinc-400"}`} />
                <span className="text-[10px] text-muted-foreground">{isConnected ? "Live" : "..."}</span>
              </div>
            </div>

            <Terminal lines={lines} isActive={running} currentPhase={currentPhase}
              collapsed={terminalCollapsed} onToggleCollapse={() => setTerminalCollapsed(!terminalCollapsed)}
              maxHeight="420px" />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md border border-red-400/30 bg-red-400/5 p-3">
          <div className="flex items-start gap-2">
            <XCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium">Error</p>
              <pre className="mt-1 text-xs font-mono text-muted-foreground whitespace-pre-wrap">{error}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Results — Diff view */}
      {results?.result && (
        <DiffResults originalContent={originalContent} results={results} />
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
      <div className="rounded-md border border-border p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {results.result.drift_fixed || !results.result.drift_detected ? (
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
          ) : (
            <AlertCircle className="h-5 w-5 text-amber-500" />
          )}
          <div>
            <span className="text-sm font-medium">{results.result.message}</span>
            {results.result.iterations_needed > 0 && (
              <span className="text-xs text-muted-foreground ml-2">({results.result.iterations_needed} iteration(s))</span>
            )}
          </div>
        </div>
        {results.result.final_files && (
          <button onClick={() => {
            const all = Object.entries(results.result.final_files as Record<string, string>)
              .map(([f, c]) => `# --- ${f} ---\n${c}`).join("\n\n");
            const blob = new Blob([all], { type: "text/plain" });
            const url = URL.createObjectURL(blob); const a = document.createElement("a");
            a.href = url; a.download = "drift-fixed.tf"; a.click(); URL.revokeObjectURL(url);
          }} className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted/50 transition-colors">
            <Download className="h-3 w-3" /> Download
          </button>
        )}
      </div>

      {results.result.drift_detected && !results.result.drift_fixed && results.result.remaining_drift && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
          <p className="text-xs font-semibold mb-1">Unresolved Drift</p>
          <pre className="text-[10px] font-mono text-muted-foreground whitespace-pre-wrap max-h-32 overflow-y-auto">{results.result.remaining_drift}</pre>
        </div>
      )}

      {diff.hasChanges && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 rounded-md border border-border overflow-hidden">
          <div className="border-r border-border overflow-hidden flex flex-col">
            <div className="px-3 py-2 border-b border-border bg-red-500/5">
              <span className="text-xs font-semibold text-red-400 uppercase tracking-wider">Original</span>
            </div>
            <div className="flex-1 overflow-auto max-h-[500px] bg-background">
              {diff.left.map((line, i) => (
                <div key={i} className={`flex text-xs font-mono leading-5 ${
                  line.state === "removed" ? "bg-red-500/[0.07] border-l-2 border-red-400/50" : line.state === "padding" ? "bg-muted/20" : ""}`}>
                  <span className="w-8 flex-shrink-0 text-right pr-1.5 py-px text-[10px] text-muted-foreground select-none border-r border-border">
                    {line.lineNumber || ""}
                  </span>
                  <span className={`flex-1 px-2 py-px whitespace-pre-wrap break-all ${line.state === "removed" ? "text-red-300" : ""}`}>
                    {line.state === "padding" ? "\u00A0" : line.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="overflow-hidden flex flex-col">
            <div className="px-3 py-2 border-b border-border bg-emerald-500/5">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Fixed</span>
            </div>
            <div className="flex-1 overflow-auto max-h-[500px] bg-background">
              {diff.right.map((line, i) => (
                <div key={i} className={`flex text-xs font-mono leading-5 ${
                  line.state === "added" ? "bg-emerald-500/[0.07] border-l-2 border-emerald-400/50" : line.state === "padding" ? "bg-muted/20" : ""}`}>
                  <span className="w-8 flex-shrink-0 text-right pr-1.5 py-px text-[10px] text-muted-foreground select-none border-r border-border">
                    {line.lineNumber || ""}
                  </span>
                  <span className={`flex-1 px-2 py-px whitespace-pre-wrap break-all ${line.state === "added" ? "text-emerald-300" : ""}`}>
                    {line.state === "padding" ? "\u00A0" : line.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {!diff.hasChanges && results.result.final_files && (
        <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-6 text-center">
          <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
          <p className="text-sm font-medium">No changes needed — code matches infrastructure.</p>
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
