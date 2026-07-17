"use client";

import { useEffect, useState } from "react";
import {
  Settings,
  BrainCircuit,
  Check,
  Trash2,
  ExternalLink,
  AlertCircle,
  Eye,
  EyeOff,
  Sparkles,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { PROVIDER_LOGOS } from "@/components/ProviderLogos";

interface ProviderInfo {
  provider: string;
  name: string;
  url: string;
  instructions: string[];
  placeholder: string;
  configured: boolean;
  enabled: boolean;
  model: string;
  endpoint_url: string;
  api_key_masked: string;
  default_model: string;
  available_models: string[];
}

interface AISettingsData {
  active_provider: string | null;
  is_configured: boolean;
  providers: ProviderInfo[];
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AISettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [formState, setFormState] = useState<Record<string, { apiKey: string; model: string; endpoint: string }>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchSettings = async () => {
    try {
      const data = await apiClient.getAISettings();
      setSettings(data);
    } catch {
      setSettings(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSettings(); }, []);

  const configureProvider = async (provider: string) => {
    const form = formState[provider];
    if (!form) return;

    setSaving(provider);
    setMessage(null);
    try {
      await apiClient.configureAIProvider({
        provider,
        api_key: form.apiKey,
        model: form.model,
        endpoint_url: form.endpoint,
      });
      setMessage({ type: "success", text: `${provider} configured successfully` });
      await fetchSettings();
      setExpandedProvider(null);
    } catch (e) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Configuration failed" });
    } finally {
      setSaving(null);
    }
  };

  const activateProvider = async (provider: string) => {
    try {
      await apiClient.activateAIProvider(provider);
      await fetchSettings();
      setMessage({ type: "success", text: `${provider} is now active` });
    } catch (e) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Activation failed" });
    }
  };

  const removeProvider = async (provider: string) => {
    try {
      await apiClient.removeAIProvider(provider);
      await fetchSettings();
      setMessage({ type: "success", text: `${provider} removed` });
    } catch (e) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Remove failed" });
    }
  };

  const toggleExpand = (provider: string) => {
    if (expandedProvider === provider) {
      setExpandedProvider(null);
    } else {
      setExpandedProvider(provider);
      const existing = settings?.providers.find((p) => p.provider === provider);
      setFormState((prev) => ({
        ...prev,
        [provider]: {
          apiKey: "",
          model: existing?.model || existing?.default_model || "",
          endpoint: existing?.endpoint_url || "",
        },
      }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 shadow-sm">
          <Settings className="h-4 w-4 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground">Configure AI providers for code cleaning.</p>
        </div>
      </div>

      {/* Status Banner */}
      {settings && !settings.is_configured && (
        <div className="rounded-xl border border-amber-200 dark:border-amber-500/20 bg-amber-50 dark:bg-amber-500/5 p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
              No AI provider configured
            </p>
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
              Code cleaning options are not available. Configure an AI provider below to enable them.
            </p>
          </div>
        </div>
      )}

      {settings?.is_configured && (
        <div className="rounded-xl border border-green-200 dark:border-green-500/20 bg-green-50 dark:bg-green-500/5 p-4 flex items-center gap-3">
          <Sparkles className="h-5 w-5 text-green-500 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-green-800 dark:text-green-300">
              AI configured — Active provider: <span className="font-semibold">{settings.active_provider}</span>
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
              AI code cleaning is available on the Generate page.
            </p>
          </div>
        </div>
      )}

      {/* Message */}
      {message && (
        <div className={`rounded-xl border p-3 text-sm animate-slide-up ${
          message.type === "success"
            ? "border-green-200 dark:border-green-500/20 bg-green-50 dark:bg-green-500/5 text-green-700 dark:text-green-300"
            : "border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-500/5 text-red-700 dark:text-red-300"
        }`}>
          {message.text}
        </div>
      )}

      {/* Provider List */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <BrainCircuit className="h-3.5 w-3.5" />
          AI Providers
        </h3>

        {settings?.providers.map((provider) => (
          <div
            key={provider.provider}
            className={`rounded-xl border transition-all duration-200 ${
              settings.active_provider === provider.provider
                ? "border-primary/30 bg-primary/5"
                : "border-border bg-card/50"
            }`}
          >
            {/* Provider Header */}
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${
                  provider.configured ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
                }`} />
                <div className="flex items-center gap-2">
                  {(() => {
                    const Logo = PROVIDER_LOGOS[provider.provider];
                    return Logo ? <Logo className="h-4 w-4 text-muted-foreground" /> : null;
                  })()}
                  <div>
                    <p className="text-sm font-medium">{provider.name}</p>
                    {provider.configured && (
                      <p className="text-[10px] text-muted-foreground">
                        Key: {provider.api_key_masked} · Model: {provider.model}
                      </p>
                    )}
                  </div>
                </div>
                {settings.active_provider === provider.provider && (
                  <span className="rounded-full bg-primary/10 border border-primary/30 px-2 py-0.5 text-[10px] font-medium text-primary">
                    Active
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {provider.configured && settings.active_provider !== provider.provider && (
                  <button
                    onClick={() => activateProvider(provider.provider)}
                    className="text-xs text-primary hover:text-primary/80 px-2 py-1 rounded hover:bg-accent transition-colors"
                  >
                    Activate
                  </button>
                )}
                {provider.configured && (
                  <button
                    onClick={() => {
                      if (confirm(`Remove ${provider.name} configuration? This will delete the stored API key.`)) {
                        removeProvider(provider.provider);
                      }
                    }}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                    aria-label={`Remove ${provider.name} configuration`}
                    title="Remove API key and configuration"
                  >
                    <Trash2 className="h-3 w-3" />
                    <span>Remove</span>
                  </button>
                )}
                <button
                  onClick={() => toggleExpand(provider.provider)}
                  className="text-xs font-medium text-primary hover:text-primary/80 px-2 py-1 rounded hover:bg-accent transition-colors"
                >
                  {expandedProvider === provider.provider ? "Close" : "Configure"}
                </button>
              </div>
            </div>

            {/* Expanded Configuration Form */}
            {expandedProvider === provider.provider && (
              <div className="px-4 pb-4 pt-0 border-t border-border/50 mt-0">
                <div className="pt-4 space-y-4">
                  {/* Instructions */}
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-xs font-medium mb-2">Setup Instructions:</p>
                    <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
                      {provider.instructions.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                    {provider.url && (
                      <a
                        href={provider.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline"
                      >
                        Open provider console <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>

                  {/* Form Fields */}
                  <div className="grid gap-3">
                    {provider.provider !== "ollama" && (
                      <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">API Key</label>
                        <input
                          type="password"
                          value={formState[provider.provider]?.apiKey || ""}
                          onChange={(e) => setFormState((prev) => ({
                            ...prev,
                            [provider.provider]: { ...prev[provider.provider], apiKey: e.target.value },
                          }))}
                          placeholder={provider.placeholder}
                          className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                        />
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">Model</label>
                        <select
                          value={formState[provider.provider]?.model || ""}
                          onChange={(e) => setFormState((prev) => ({
                            ...prev,
                            [provider.provider]: { ...prev[provider.provider], model: e.target.value },
                          }))}
                          className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                        >
                          {provider.available_models.map((model) => (
                            <option key={model} value={model}>
                              {model}{model === provider.default_model ? " (default)" : ""}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">
                          Endpoint URL <span className="text-muted-foreground/50">(optional)</span>
                        </label>
                        <input
                          type="text"
                          value={formState[provider.provider]?.endpoint || ""}
                          onChange={(e) => setFormState((prev) => ({
                            ...prev,
                            [provider.provider]: { ...prev[provider.provider], endpoint: e.target.value },
                          }))}
                          placeholder={provider.provider === "ollama" ? "http://localhost:11434" : ""}
                          className="w-full rounded-lg border bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Save Button */}
                  <button
                    onClick={() => configureProvider(provider.provider)}
                    disabled={saving === provider.provider}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all"
                  >
                    {saving === provider.provider ? (
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    ) : (
                      <Check className="h-3.5 w-3.5" />
                    )}
                    Save Configuration
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
