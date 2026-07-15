"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Code, Download, Copy, Check, FileText, Play, Database } from "lucide-react";
import { apiClient } from "@/lib/api";
import type { GenerationResult } from "@/lib/api";

export default function GeneratePage() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job_id");
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Backend state config
  const [stateBucket, setStateBucket] = useState("");
  const [statePrefix, setStatePrefix] = useState("terraform/state");

  // Output format
  const [outputFormat, setOutputFormat] = useState<"single_file" | "per_resource_type">(
    "per_resource_type"
  );

  const generate = async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);

    try {
      const genResult = await apiClient.generateTerraform({
        job_id: jobId,
        resource_ids: ["all"],
        options: {
          include_provider_block: true,
          include_import_script: true,
          output_format: outputFormat,
          backend_state: stateBucket.trim()
            ? { bucket: stateBucket.trim(), prefix: statePrefix.trim() }
            : undefined,
        },
      });
      setResult(genResult);
      if (genResult.files.length > 0) setActiveFile(genResult.files[0].filename);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const activeContent =
    result?.files.find((f) => f.filename === activeFile)?.content || "";

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(activeContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!jobId) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Generate Terraform</h1>
          <p className="text-muted-foreground">
            Generate Terraform code from discovered resources.
          </p>
        </div>
        <div className="rounded-lg border bg-card p-8 text-center">
          <Code className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">
            No discovery results selected. Go to{" "}
            <a href="/discover" className="text-primary underline">
              Discover
            </a>{" "}
            first.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Generate Terraform</h1>
        <p className="text-muted-foreground">
          Configure generation options and generate Terraform code.
        </p>
      </div>

      {/* Generation Options */}
      <div className="rounded-lg border bg-card p-6 space-y-4">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <Database className="h-4 w-4" />
          Generation Options
        </h3>

        {/* Output Format */}
        <div>
          <label className="block text-xs text-muted-foreground mb-1.5">
            Output Format
          </label>
          <select
            value={outputFormat}
            onChange={(e) =>
              setOutputFormat(e.target.value as "single_file" | "per_resource_type")
            }
            className="w-full max-w-xs rounded-md border bg-background px-3 py-2 text-sm"
            disabled={loading}
          >
            <option value="per_resource_type">One file per resource type</option>
            <option value="single_file">Single file (main.tf)</option>
          </select>
        </div>

        {/* Backend State Configuration */}
        <div className="border-t pt-4">
          <h4 className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
            Remote State (GCS Backend)
          </h4>
          <p className="text-xs text-muted-foreground mb-3">
            Optional. If provided, a <code className="rounded bg-muted px-1 py-0.5">backend.tf</code> file
            will be generated to store Terraform state remotely in a GCS bucket.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-muted-foreground mb-1.5">
                Bucket Name
              </label>
              <input
                type="text"
                value={stateBucket}
                onChange={(e) => setStateBucket(e.target.value)}
                placeholder="my-terraform-state-bucket"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                disabled={loading}
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1.5">
                Prefix (path)
              </label>
              <input
                type="text"
                value={statePrefix}
                onChange={(e) => setStatePrefix(e.target.value)}
                placeholder="terraform/state/pro"
                className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                disabled={loading}
              />
            </div>
          </div>
        </div>

        {/* Generate Button */}
        <button
          onClick={generate}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {loading ? "Generating..." : "Generate Terraform"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Generated {result.total_resources} resources across{" "}
              {result.files.length} files
            </p>
            <a
              href={apiClient.getDownloadUrl(jobId)}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Download className="h-4 w-4" />
              Download ZIP
            </a>
          </div>

          <div className="grid grid-cols-12 gap-4 h-[calc(100vh-520px)]">
            {/* File List */}
            <div className="col-span-3 rounded-lg border bg-card overflow-y-auto">
              <div className="p-3 border-b">
                <h3 className="text-xs font-medium text-muted-foreground uppercase">
                  Files
                </h3>
              </div>
              <div className="p-2 space-y-1">
                {result.files.map((file) => (
                  <button
                    key={file.filename}
                    onClick={() => setActiveFile(file.filename)}
                    className={`w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm text-left transition-colors ${
                      activeFile === file.filename
                        ? "bg-secondary text-secondary-foreground"
                        : "text-muted-foreground hover:bg-accent"
                    }`}
                  >
                    <FileText className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="truncate">{file.filename}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Code Preview */}
            <div className="col-span-9 rounded-lg border bg-card flex flex-col overflow-hidden">
              <div className="flex items-center justify-between border-b px-4 py-2">
                <span className="text-sm font-mono text-muted-foreground">
                  {activeFile}
                </span>
                <button
                  onClick={copyToClipboard}
                  className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs hover:bg-accent transition-colors"
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-green-500" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <pre className="flex-1 overflow-auto p-4 text-xs font-mono leading-relaxed bg-muted/30">
                <code>{activeContent}</code>
              </pre>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
