"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import {
  Upload,
  FileText,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Play,
  Square,
  Circle,
  Download,
  BrainCircuit,
  Trash2,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import Terminal, { type TerminalLine } from "@/components/Terminal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const phases = [
  { key: "init", label: "Init" },
  { key: "plan", label: "Plan" },
  { key: "fix", label: "AI Fix" },
  { key: "import", label: "Import" },
  { key: "verify", label: "Verify" },
  { key: "decision", label: "Decision" },
  { key: "done", label: "Done" },
];

// WebSocket hook for auto-import
function useAutoImportWebSocket(jobId: string | null) {
  const [lines, setLines] = useState<TerminalLine[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [currentPhase, setCurrentPhase] = useState("init");
  const [phaseMessage, setPhaseMessage] = useState("");
  const [isComplete, setIsComplete] = useState(false);
  const [driftDecision, setDriftDecision] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const isCompleteRef = useRef(false);
  const reconnectRef = useRef(0);

  useEffect(() => { isCompleteRef.current = isComplete; }, [isComplete]);

  const connect = useCallback((id: string) => {
    if (isCompleteRef.current) return;
    const wsBase = API_URL.replace("http://", "ws://").replace("https://", "wss://").replace("/api/v1", "");
    const ws = new WebSocket(`${wsBase}/ws/auto-import/${id}`);
    wsRef.current = ws;

    ws.onopen = () => { setIsConnected(true); setError(null); reconnectRef.current = 0; };
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "log":
            if (msg.data) {
              setLines((prev) => {
                const updated = [...prev, { text: msg.data.line || "", stream: msg.data.stream || "stdout", phase: msg.data.phase || "init", timestamp: msg.data.timestamp || Date.now() / 1000 }];
                return updated.length > 10000 ? updated.slice(-10000) : updated;
              });
            }
            break;
          case "phase":
            if (msg.data?.phase) { setCurrentPhase(msg.data.phase); setPhaseMessage(msg.data.message || ""); }
            break;
          case "complete":
            setIsComplete(true); isCompleteRef.current = true; setCurrentPhase("done");
            break;
          case "drift_decision":
            setDriftDecision(msg.data?.drift || null); setCurrentPhase("decision");
            break;
          case "error":
            setError(msg.data?.message || "Unknown error");
            break;
        }
      } catch {}
    };
    ws.onclose = (event) => {
      setIsConnected(false); wsRef.current = null;
      if (!isCompleteRef.current && event.code !== 1000 && event.code !== 1008 && reconnectRef.current < 3) {
        reconnectRef.current++;
        setTimeout(() => { if (!isCompleteRef.current) connect(id); }, 2000);
      }
    };
    ws.onerror = () => {};
  }, []);

  useEffect(() => {
    if (!jobId) { setLines([]); setIsConnected(false); setCurrentPhase("init"); setPhaseMessage(""); setIsComplete(false); setDriftDecision(null); setError(null); return; }
    setLines([]); setIsComplete(false); setError(null); setCurrentPhase("init"); setPhaseMessage(""); setDriftDecision(null); isCompleteRef.current = false; reconnectRef.current = 0;
    connect(jobId);
    return () => { if (wsRef.current) { wsRef.current.close(1000); wsRef.current = null; } };
  }, [jobId, connect]);

  return { lines, isConnected, currentPhase, phaseMessage, isComplete, driftDecision, error };
}

function AutoImportContent() {
  const [files, setFiles] = useState<Record<string, string>>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<any>(null);
  const [terminalCollapsed, setTerminalCollapsed] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const { lines, isConnected, currentPhase, phaseMessage, isComplete, driftDecision, error: wsError } = useAutoImportWebSocket(jobId);

  // Handle completion
  useEffect(() => {
    if (isComplete && jobId) {
      apiClient.request<any>(`/auto-import/results/${jobId}`)
        .then(setResults)
        .catch(() => {})
        .finally(() => { setRunning(false); setCancelling(false); });
    }
  }, [isComplete, jobId]);

  const hasBackendTf = Object.keys(files).some((f) => f.toLowerCase() === "backend.tf");
  const hasJob = jobId !== null;

  // File handling
  const processFiles = (fileList: FileList | File[]) => {
    const newFiles: Record<string, string> = { ...files };
    Array.from(fileList).forEach((file) => {
      if (file.name.endsWith(".tf") || file.name.endsWith(".tf.json")) {
        const reader = new FileReader();
        reader.onload = (e) => {
          newFiles[file.name] = e.target?.result as string;
          setFiles({ ...newFiles });
        };
        reader.readAsText(file);
      }
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    processFiles(e.dataTransfer.files);
  };

  const removeFile = (filename: string) => {
    const updated = { ...files };
    delete updated[filename];
    setFiles(updated);
  };

  const startImport = async () => {
    if (!hasBackendTf) {
      setError("backend.tf is required. Please upload your backend configuration file.");
      return;
    }
    if (Object.keys(files).length < 2) {
      setError("Upload at least one resource .tf file in addition to backend.tf.");
      return;
    }

    setError(null); setRunning(true); setResults(null); setTerminalCollapsed(false); setCancelling(false);

    try {
      const job = await apiClient.request<{ job_id: string }>("/auto-import/start", {
        method: "POST", body: JSON.stringify({ tf_files: files }),
      });
      setJobId(job.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start auto-import");
      setRunning(false);
    }
  };

  const stopImport = async () => {
    if (!jobId) return;
    setCancelling(true);
    try { await apiClient.request(`/auto-import/cancel/${jobId}`, { method: "POST" }); } catch {}
  };

  const submitDecision = async (decision: string) => {
    if (!jobId) return;
    try {
      await apiClient.request(`/auto-import/decision/${jobId}`, {
        method: "POST", body: JSON.stringify({ decision }),
      });
    } catch {}
  };

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 shadow-sm">
          <Upload className="h-4 w-4 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Auto Import</h1>
          <p className="text-sm text-muted-foreground">
            Upload your Terraform files and import existing infrastructure into state automatically.
          </p>
        </div>
      </div>

      {/* Main layout */}
      <div className={`grid grid-cols-1 gap-4 ${hasJob ? "lg:grid-cols-12" : "lg:grid-cols-2"}`}>
        {/* Left: Upload zone */}
        <div className={`${hasJob ? "lg:col-span-4" : ""} space-y-4`}>
          {/* Drop zone */}
          <div
            ref={dropRef}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-500/10"
                : "border-gray-300 dark:border-white/10 hover:border-emerald-400 hover:bg-emerald-50/50 dark:hover:bg-emerald-500/5"
            } ${running ? "opacity-50 pointer-events-none" : ""}`}
          >
            <Upload className={`h-8 w-8 mx-auto mb-3 ${dragOver ? "text-emerald-500" : "text-gray-400"}`} />
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Drop .tf files here or click to browse
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              backend.tf is <span className="font-semibold text-amber-600 dark:text-amber-400">required</span>
            </p>
            <input
              ref={fileInputRef} type="file" multiple accept=".tf,.tf.json"
              onChange={(e) => e.target.files && processFiles(e.target.files)}
              className="hidden"
            />
          </div>

          {/* File list */}
          {Object.keys(files).length > 0 && (
            <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] overflow-hidden">
              <div className="px-4 py-2.5 border-b border-border/50 bg-muted/20">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Uploaded Files ({Object.keys(files).length})
                </span>
              </div>
              <div className="p-2 space-y-1 max-h-48 overflow-y-auto">
                {Object.entries(files).map(([name, content]) => (
                  <div key={name} className="flex items-center justify-between px-3 py-1.5 rounded-lg hover:bg-muted/30">
                    <div className="flex items-center gap-2">
                      <FileText className="h-3.5 w-3.5 text-gray-400" />
                      <span className="text-xs font-mono">{name}</span>
                      {name.toLowerCase() === "backend.tf" && (
                        <span className="text-[9px] bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 px-1.5 py-0.5 rounded font-medium">required</span>
                      )}
                    </div>
                    <button onClick={() => removeFile(name)} disabled={running} className="p-1 hover:bg-red-50 dark:hover:bg-red-500/10 rounded text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50">
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Validation message */}
          {Object.keys(files).length > 0 && !hasBackendTf && (
            <div className="rounded-lg border border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/5 p-3 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-amber-700 dark:text-amber-300">
                <span className="font-semibold">backend.tf is missing.</span> This file is required to configure the remote state for importing resources.
              </p>
            </div>
          )}

          {/* Action buttons */}
          <div className="space-y-2">
            <button
              onClick={startImport}
              disabled={running || !hasBackendTf || Object.keys(files).length < 2}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-b from-emerald-500 to-emerald-600 text-white text-sm font-medium shadow-sm hover:from-emerald-400 hover:to-emerald-500 active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? "Importing..." : "Start Auto Import"}
            </button>
            {running && (
              <button onClick={stopImport} disabled={cancelling}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-b from-red-500 to-red-600 text-white text-sm font-medium shadow-sm hover:from-red-400 hover:to-red-500 active:scale-[0.98] transition-all disabled:opacity-50">
                <Square className="h-3.5 w-3.5 fill-current" />
                {cancelling ? "Stopping..." : "Stop"}
              </button>
            )}
          </div>
        </div>

        {/* Right: Terminal */}
        {hasJob && (
          <div className="lg:col-span-8 flex flex-col space-y-2 animate-slide-up">
            {/* Phase indicator */}
            <div className="flex items-center gap-1 flex-wrap">
              {phases.map((phase, i) => {
                const phaseIndex = phases.findIndex((p) => p.key === currentPhase);
                const isActive = phase.key === currentPhase;
                const isDone = i < phaseIndex || currentPhase === "done";
                return (
                  <div key={phase.key} className="flex items-center">
                    <div className={`flex items-center gap-1 px-2 py-0.5 rounded-md text-[9px] font-medium transition-all ${isActive ? "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" : isDone ? "bg-green-50 dark:bg-green-500/10 text-green-600 dark:text-green-400" : "bg-muted/50 text-muted-foreground"}`}>
                      {isActive && running && <Circle className="h-1.5 w-1.5 fill-emerald-500 animate-pulse" />}
                      {isDone && <CheckCircle2 className="h-2.5 w-2.5" />}
                      {phase.label}
                    </div>
                    {i < phases.length - 1 && <div className={`w-3 h-px mx-0.5 ${isDone ? "bg-green-300 dark:bg-green-600" : "bg-border"}`} />}
                  </div>
                );
              })}
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {running && phaseMessage && (
                  <span className="inline-flex items-center gap-1.5 text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                    <BrainCircuit className="h-3 w-3 animate-pulse" />
                    {phaseMessage}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`h-1.5 w-1.5 rounded-full ${isConnected ? "bg-green-500" : "bg-gray-400"}`} />
                <span className="text-[10px] text-muted-foreground">{isConnected ? "Live" : "..."}</span>
              </div>
            </div>

            {/* Drift decision modal */}
            {driftDecision && !isComplete && (
              <div className="rounded-xl border border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/5 p-4 space-y-3 animate-slide-up">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-amber-500 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-amber-800 dark:text-amber-200">Drift Detected After Import</p>
                    <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
                      {driftDecision.changed} to change, {driftDecision.destroyed} to destroy, {driftDecision.added} to add
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => submitDecision("fix")} className="flex-1 px-3 py-2 rounded-lg bg-indigo-500 text-white text-xs font-medium hover:bg-indigo-600 transition-colors">
                    Fix with AI
                  </button>
                  <button onClick={() => submitDecision("download")} className="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-white/10 text-xs font-medium hover:bg-muted/50 transition-colors">
                    Download Plan
                  </button>
                  <button onClick={() => submitDecision("ignore")} className="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-white/10 text-xs font-medium hover:bg-muted/50 transition-colors">
                    Ignore
                  </button>
                </div>
              </div>
            )}

            {/* Terminal */}
            <Terminal
              lines={lines} isActive={running} currentPhase={currentPhase}
              collapsed={terminalCollapsed} onToggleCollapse={() => setTerminalCollapsed(!terminalCollapsed)}
              maxHeight="450px"
            />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-500/5 p-4">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800 dark:text-red-200">Error</p>
              <pre className="mt-1 text-xs font-mono text-red-700 dark:text-red-300 whitespace-pre-wrap">{error}</pre>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {results?.result && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 animate-slide-up">
          <div className="flex items-center gap-3 mb-4">
            {results.result.drift === false ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : (
              <AlertCircle className="h-5 w-5 text-amber-500" />
            )}
            <p className="text-sm font-medium">{results.result.message}</p>
          </div>
          {results.result.final_files && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase">Final Files</span>
                <button
                  onClick={() => {
                    const all = Object.entries(results.result.final_files as Record<string, string>).map(([f, c]) => `# --- ${f} ---\n${c}`).join("\n\n");
                    const blob = new Blob([all], { type: "text/plain" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a"); a.href = url; a.download = "auto-import-result.tf"; a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-medium hover:bg-muted/50 transition-colors"
                >
                  <Download className="h-3 w-3" /> Download All
                </button>
              </div>
              <div className="rounded-lg border overflow-hidden max-h-[400px] overflow-y-auto">
                {Object.entries(results.result.final_files as Record<string, string>).map(([filename, content]) => (
                  <div key={filename}>
                    <div className="px-3 py-1.5 bg-muted/30 border-b flex items-center justify-between">
                      <span className="text-[10px] font-mono text-muted-foreground">{filename}</span>
                      <button onClick={() => navigator.clipboard.writeText(content)} className="text-[10px] text-primary hover:underline">Copy</button>
                    </div>
                    <pre className="p-3 text-xs font-mono overflow-x-auto border-b">{content}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AutoImportPage() {
  return (
    <Suspense fallback={<div className="animate-pulse p-8 text-muted-foreground">Loading...</div>}>
      <AutoImportContent />
    </Suspense>
  );
}
