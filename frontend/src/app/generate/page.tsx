"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Code, Download, Copy, Check, FileText, Sparkles, Database, FileCode, BrainCircuit, RefreshCw } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { GenerationResult } from "@/lib/api";

function Loader2Icon({ className }: { className?: string }) {
  return (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function highlightTerraform(content: string): JSX.Element[] {
  const lines = content.split("\n");
  return lines.map((line, idx) => {
    let highlighted = line;

    // Comments
    if (line.trim().startsWith("#") || line.trim().startsWith("//")) {
      return (
        <div key={idx} className="flex">
          <span className="select-none w-8 text-right text-gray-300 dark:text-gray-600 mr-4 text-[12px]">
            {idx + 1}
          </span>
          <span className="text-gray-400 dark:text-gray-500 italic">{line}</span>
        </div>
      );
    }

    // Build highlighted spans
    const parts: JSX.Element[] = [];
    let remaining = line;
    let partKey = 0;

    // Match keywords at start
    const keywordMatch = remaining.match(/^(\s*)(resource|data|variable|output|locals|module|provider|terraform)(\s)/);
    if (keywordMatch) {
      parts.push(<span key={partKey++}>{keywordMatch[1]}</span>);
      parts.push(<span key={partKey++} className="text-violet-600 dark:text-violet-400">{keywordMatch[2]}</span>);
      remaining = remaining.slice(keywordMatch[0].length - 1);
    }

    // Simple token-based highlighting for remaining content
    const tokens = remaining.split(/("(?:[^"\\]|\\.)*")/);
    tokens.forEach((token, tIdx) => {
      if (token.startsWith('"') && token.endsWith('"')) {
        // String literals
        parts.push(
          <span key={partKey++} className="text-emerald-600 dark:text-emerald-400">{token}</span>
        );
      } else {
        // Check for = sign, numbers, booleans
        const subTokens = token.split(/(\b(?:true|false|null)\b|\b\d+\b|[{}[\]=])/);
        subTokens.forEach((sub, sIdx) => {
          if (sub === "true" || sub === "false" || sub === "null") {
            parts.push(<span key={partKey++} className="text-amber-600 dark:text-amber-400">{sub}</span>);
          } else if (/^\d+$/.test(sub)) {
            parts.push(<span key={partKey++} className="text-sky-600 dark:text-sky-400">{sub}</span>);
          } else if (sub === "{" || sub === "}" || sub === "[" || sub === "]") {
            parts.push(<span key={partKey++} className="text-gray-500 dark:text-gray-400">{sub}</span>);
          } else if (sub === "=") {
            parts.push(<span key={partKey++} className="text-gray-400 dark:text-gray-500">{sub}</span>);
          } else {
            parts.push(<span key={partKey++} className="text-gray-900 dark:text-gray-200">{sub}</span>);
          }
        });
      }
    });

    return (
      <div key={idx} className="flex hover:bg-gray-50 dark:hover:bg-white/[0.02] -mx-4 px-4 transition-colors">
        <span className="select-none w-8 text-right text-gray-300 dark:text-gray-600 mr-4 text-[12px]">
          {idx + 1}
        </span>
        <span>{parts}</span>
      </div>
    );
  });
}

export default function GeneratePage() {
  return (
    <Suspense fallback={
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 shadow-sm">
            <Code className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-[-0.025em] text-gray-900 dark:text-white">
              Generate Terraform
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading...</p>
          </div>
        </div>
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-10 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        </div>
      </div>
    }>
      <GeneratePageContent />
    </Suspense>
  );
}

function GenerationHistoryPanel() {
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    apiClient.request<any>("/generations?limit=5")
      .then((data) => setHistory(data.generations || []))
      .catch(() => {});
  }, []);

  if (history.length === 0) return null;

  return (
    <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-5 mt-4">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
        Previous Generations
      </h4>
      <div className="space-y-2">
        {history.map((gen) => (
          <a
            key={gen.id}
            href={`/generate?generation_id=${gen.id}`}
            className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-gray-50 dark:hover:bg-white/[0.03] transition-colors border border-transparent hover:border-gray-200 dark:hover:border-white/[0.06]"
          >
            <div className="flex items-center gap-3">
              <FileText className="h-4 w-4 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {gen.total_resources} resources · {gen.files_count} files
                </p>
                <p className="text-[10px] text-gray-400">
                  {gen.style} {gen.ai_cleaned ? "· AI cleaned" : ""} · {gen.created_at?.replace("T", " ").slice(0, 16)}
                </p>
              </div>
            </div>
            <span className="text-[10px] text-primary">View →</span>
          </a>
        ))}
      </div>
    </div>
  );
}

function GeneratePageContent() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job_id");
  const generationId = searchParams.get("generation_id");
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [stateBucket, setStateBucket] = useState("");
  const [statePrefix, setStatePrefix] = useState("terraform/state");
  const [outputFormat, setOutputFormat] = useState<"single_file" | "per_resource_type">("per_resource_type");
  const [generationStyle, setGenerationStyle] = useState<"flat" | "module">("flat");
  const [aiClean, setAiClean] = useState(false);
  const [aiConfigured, setAiConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    apiClient.getAIStatus().then((s) => setAiConfigured(s.configured)).catch(() => setAiConfigured(false));
  }, []);

  // Load previous generation from history if generation_id is in URL
  useEffect(() => {
    if (generationId) {
      setLoading(true);
      apiClient.request<any>(`/generations/${generationId}`)
        .then((data) => {
          if (data && data.files) {
            const files = data.files.map((f: any) => ({ filename: f.filename, content: f.content }));
            setResult({
              files,
              total_resources: data.total_resources || 0,
              import_commands: data.total_resources || 0,
              ai_cleaned: Boolean(data.ai_cleaned),
              ai_diff: null,
            });
            if (files.length > 0) setActiveFile(files[0].filename);
          }
        })
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load generation"))
        .finally(() => setLoading(false));
    }
  }, [generationId]);

  const generate = async () => {
    if (!jobId) return;
    setLoading(true); setError(null);
    try {
      const r = await apiClient.generateTerraform({
        job_id: jobId,
        resource_ids: ["all"],
        options: {
          include_provider_block: true,
          include_import_script: true,
          output_format: outputFormat,
          generation_style: generationStyle,
          ai_clean: aiClean,
          backend_state: stateBucket.trim() ? { bucket: stateBucket.trim(), prefix: statePrefix.trim() } : undefined,
        },
      });
      setResult(r);
      if (r.files.length > 0) setActiveFile(r.files[0].filename);
    } catch (e) { setError(e instanceof Error ? e.message : "Generation failed"); }
    finally { setLoading(false); }
  };

  const activeContent = result?.files.find((f) => f.filename === activeFile)?.content || "";
  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(activeContent);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  };

  if (!jobId && !generationId) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 shadow-sm">
            <Code className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-[-0.025em] text-gray-900 dark:text-white">
              Generate Terraform
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">Generate Terraform code from discovered resources.</p>
          </div>
        </div>
        {/* Empty state */}
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-12 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gray-100 dark:bg-white/[0.04] mb-4">
            <Code className="h-7 w-7 text-gray-300 dark:text-gray-600" />
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">No discovery results selected</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Go to{" "}
            <a href="/discover" className="text-indigo-500 font-medium hover:text-indigo-600 transition-colors">Discover</a>{" "}
            first to scan your infrastructure.
          </p>
        </div>

        {/* Previous Generations */}
        <GenerationHistoryPanel />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 shadow-sm">
          <Code className="h-4 w-4 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-[-0.025em] text-gray-900 dark:text-white">
            Generate Terraform
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Configure options and generate IaC code.</p>
        </div>
      </div>

      {/* Options */}
      <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-6 space-y-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2">
          <Database className="h-3.5 w-3.5" />
          Generation Options
        </h3>

        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Output Format</label>
          <select
            value={outputFormat}
            onChange={(e) => setOutputFormat(e.target.value as "single_file" | "per_resource_type")}
            className="w-full max-w-xs rounded-lg border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.03] px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none transition-all"
            disabled={loading}
          >
            <option value="per_resource_type">One file per resource type</option>
            <option value="single_file">Single file (main.tf)</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Generation Style</label>
          <select
            value={generationStyle}
            onChange={(e) => setGenerationStyle(e.target.value as "flat" | "module")}
            className="w-full max-w-xs rounded-lg border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.03] px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none transition-all"
            disabled={loading}
          >
            <option value="flat">Flat Resources (resource blocks)</option>
            <option value="module">Modules (official Google Cloud modules)</option>
          </select>
          <p className="text-[11px] text-gray-400 dark:text-gray-500 mt-1.5">
            {generationStyle === "flat"
              ? "Generates standard resource blocks — full control over every attribute."
              : "Uses official terraform-google-modules from the Terraform Registry — best practices baked in."}
          </p>
        </div>

        {/* AI Code Cleaning */}
        <div className="border-t border-gray-100 dark:border-white/[0.04] pt-5">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                <BrainCircuit className="h-3.5 w-3.5" />
                AI Code Cleaning
              </h4>
              <p className="text-xs text-muted-foreground mt-1">
                {aiConfigured === false
                  ? "No AI provider configured. Set one up in Settings to enable code cleaning."
                  : "Use AI to remove default values and unnecessary attributes from generated HCL."}
              </p>
            </div>
            <button
              onClick={() => setAiClean(!aiClean)}
              disabled={!aiConfigured || loading}
              className={`relative w-11 h-6 rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                aiClean && aiConfigured ? "bg-primary" : "bg-gray-200 dark:bg-gray-700"
              } ${!aiConfigured ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
              aria-label="Toggle AI cleaning"
              aria-pressed={aiClean}
            >
              <div className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                aiClean && aiConfigured ? "translate-x-5" : "translate-x-0"
              }`} />
            </button>
          </div>
          {!aiConfigured && aiConfigured !== null && (
            <a href="/settings" className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline">
              Go to Settings to configure AI →
            </a>
          )}
        </div>

        {/* Backend State */}
        <div className="border-t border-gray-100 dark:border-white/[0.04] pt-5">
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wider">
            Remote State (GCS Backend)
          </h4>
          <p className="text-[11px] text-gray-400 dark:text-gray-500 mb-3">
            Optional. Generates a <code className="rounded-md bg-gray-100 dark:bg-white/[0.06] px-1.5 py-0.5 font-mono text-gray-600 dark:text-gray-300">backend.tf</code> for remote state storage.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Bucket Name</label>
              <input
                type="text" value={stateBucket} onChange={(e) => setStateBucket(e.target.value)}
                placeholder="my-terraform-state-bucket"
                className="w-full rounded-lg border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.03] px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none transition-all"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">Prefix (path)</label>
              <input
                type="text" value={statePrefix} onChange={(e) => setStatePrefix(e.target.value)}
                placeholder="terraform/state/prod"
                className="w-full rounded-lg border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.03] px-3 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500/50 outline-none transition-all"
                disabled={loading}
              />
            </div>
          </div>
        </div>

        <button
          onClick={generate} disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-b from-indigo-500 to-indigo-600 text-white text-sm font-medium shadow-[0_1px_2px_rgba(0,0,0,0.1),inset_0_1px_0_rgba(255,255,255,0.1)] hover:from-indigo-400 hover:to-indigo-500 active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none"
        >
          {loading ? <Loader2Icon className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {loading ? "Generating..." : "Generate Terraform"}
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200/60 dark:border-rose-500/20 bg-rose-50 dark:bg-rose-500/5 p-4 animate-slide-up">
          <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>
        </div>
      )}

      {loading && (
        <div className="rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] p-10 text-center animate-slide-up">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent mb-4" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Generating Terraform code...</p>
        </div>
      )}

      {result && (
        <>
          <div className="flex items-center justify-between animate-slide-up">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Generated <span className="font-semibold text-gray-900 dark:text-white">{result.total_resources}</span> resources across{" "}
              <span className="font-semibold text-gray-900 dark:text-white">{result.files.length}</span> files
            </p>
            <div className="flex items-center gap-2">
              {/* Drift Detection Button */}
              <div className="relative group">
                <a
                  href={aiConfigured ? `/drift?from_generate=true&job_id=${jobId}` : "#"}
                  onClick={(e) => { if (!aiConfigured) e.preventDefault(); }}
                  className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-all duration-150 ${
                    aiConfigured
                      ? "border border-indigo-400/60 dark:border-indigo-400/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10"
                      : "bg-gray-100 dark:bg-white/[0.04] text-gray-400 dark:text-gray-500 cursor-not-allowed"
                  }`}
                >
                  <RefreshCw className="h-4 w-4" />
                  Run Drift Detection
                </a>
                {!aiConfigured && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block whitespace-nowrap rounded-lg bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs px-3 py-1.5 shadow-lg z-10">
                    AI provider required. Configure in Settings.
                  </div>
                )}
              </div>
              <a
                href={apiClient.getDownloadUrl(jobId)}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-200 dark:border-white/[0.08] bg-white dark:bg-white/[0.03] px-3.5 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-white/[0.05] hover:border-gray-300 dark:hover:border-white/[0.12] transition-all duration-150"
              >
                <Download className="h-4 w-4" />
              Download ZIP
            </a>
            </div>
          </div>

          {/* AI Diff Preview */}
          {result.ai_cleaned && result.ai_diff && result.ai_diff.length > 0 && (
            <div className="rounded-xl border border-violet-200 dark:border-violet-500/20 bg-violet-50/50 dark:bg-violet-500/5 p-4 animate-slide-up">
              <div className="flex items-center gap-2 mb-3">
                <BrainCircuit className="h-4 w-4 text-violet-500" />
                <h4 className="text-xs font-semibold text-violet-800 dark:text-violet-300">
                  AI Cleaning Applied — {result.ai_diff.length} file(s) modified
                </h4>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {result.ai_diff.map((diff: any) => (
                  <details key={diff.filename} className="rounded-lg border border-violet-200/50 dark:border-violet-500/10 overflow-hidden">
                    <summary className="px-3 py-2 text-xs font-mono cursor-pointer hover:bg-violet-100/50 dark:hover:bg-violet-500/5 text-violet-700 dark:text-violet-300">
                      {diff.filename}
                    </summary>
                    <div className="grid grid-cols-2 gap-0 border-t border-violet-200/50 dark:border-violet-500/10">
                      <div className="p-2 border-r border-violet-200/50 dark:border-violet-500/10">
                        <p className="text-[9px] text-red-500 font-semibold mb-1 uppercase">Before</p>
                        <pre className="text-[10px] font-mono text-gray-600 dark:text-gray-400 overflow-x-auto max-h-32 overflow-y-auto">{diff.before?.slice(0, 500)}</pre>
                      </div>
                      <div className="p-2">
                        <p className="text-[9px] text-green-500 font-semibold mb-1 uppercase">After</p>
                        <pre className="text-[10px] font-mono text-gray-600 dark:text-gray-400 overflow-x-auto max-h-32 overflow-y-auto">{diff.after?.slice(0, 500)}</pre>
                      </div>
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-12 gap-4 h-[calc(100vh-520px)] animate-slide-up">
            {/* File List */}
            <div className="col-span-3 rounded-xl border border-gray-200/60 dark:border-white/[0.06] bg-white dark:bg-white/[0.02] overflow-y-auto">
              <div className="p-3 border-b border-gray-100 dark:border-white/[0.04]">
                <h3 className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Files</h3>
              </div>
              <div className="p-2 space-y-0.5">
                {result.files.map((file) => (
                  <button
                    key={file.filename}
                    onClick={() => setActiveFile(file.filename)}
                    className={`w-full flex items-center gap-2 rounded-lg px-3 py-2 text-left transition-all duration-150 ${
                      activeFile === file.filename
                        ? "bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-medium"
                        : "text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-white/[0.03] hover:text-gray-900 dark:hover:text-gray-200"
                    }`}
                  >
                    <FileText className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="truncate font-mono text-xs">{file.filename}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Code Preview — premium IDE style */}
            <div className="col-span-9 rounded-xl border border-gray-200/60 dark:border-white/[0.08] bg-white dark:bg-[#111111] overflow-hidden shadow-sm flex flex-col">
              {/* Code header — file tab style */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 dark:border-white/[0.06] bg-gray-50/50 dark:bg-white/[0.02]">
                <div className="flex items-center gap-2">
                  <FileCode className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-300">{activeFile}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={copyToClipboard}
                    className="px-2.5 py-1 text-[11px] font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-md hover:bg-gray-100 dark:hover:bg-white/[0.06] transition-colors inline-flex items-center gap-1"
                  >
                    {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                    {copied ? "Copied!" : "Copy"}
                  </button>
                  <a
                    href={apiClient.getDownloadUrl(jobId)}
                    className="px-2.5 py-1 text-[11px] font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded-md transition-colors"
                  >
                    Download
                  </a>
                </div>
              </div>

              {/* Code body with syntax highlighting */}
              <div className="flex-1 overflow-auto p-4 font-mono text-[13px] leading-6">
                {highlightTerraform(activeContent)}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
