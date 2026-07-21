"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  ArrowRight,
  ArrowLeft,
  Cloud,
  BrainCircuit,
  Rocket,
  X,
  Sparkles,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { GCPLogo, AWSLogo } from "@/components/CloudProviderLogos";

interface OnboardingSteps {
  cloud_provider: boolean;
  gcp_authenticated: boolean;
  aws_configured: boolean;
  ai_configured: boolean;
}

interface OnboardingWizardProps {
  onComplete: () => void;
  onDismiss: () => void;
}

export function OnboardingWizard({ onComplete, onDismiss }: OnboardingWizardProps) {
  const [step, setStep] = useState(0);
  const [steps, setSteps] = useState<OnboardingSteps | null>(null);

  useEffect(() => {
    refreshStatus();
  }, []);

  const refreshStatus = async () => {
    try {
      const data = await apiClient.request<any>("/onboarding/status");
      setSteps(data.steps);
      if (!data.onboarding_needed) onComplete();
    } catch {}
  };

  const totalSteps = 3;

  const stepContent = [
    // Step 0: Welcome
    {
      title: "Welcome to Terramorph",
      subtitle: "Let's get you set up in a few quick steps",
      content: (
        <div className="space-y-4 text-center py-4">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto">
            Terramorph discovers your cloud infrastructure and generates
            production-ready Terraform code. Let's configure your environment.
          </p>
          <div className="flex items-center justify-center gap-6 pt-4">
            <div className="flex flex-col items-center gap-1">
              <Cloud className="h-5 w-5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">Cloud Access</span>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground/30" />
            <div className="flex flex-col items-center gap-1">
              <BrainCircuit className="h-5 w-5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">AI (Optional)</span>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground/30" />
            <div className="flex flex-col items-center gap-1">
              <Rocket className="h-5 w-5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground">First Scan</span>
            </div>
          </div>
        </div>
      ),
    },
    // Step 1: Cloud Provider
    {
      title: "Connect a Cloud Provider",
      subtitle: "At least one provider is required to start discovering resources",
      content: (
        <div className="space-y-4 py-2">
          <div className="rounded-xl border border-border p-4 flex items-center gap-4">
            <GCPLogo className="h-8 w-8 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium">Google Cloud Platform</p>
              <p className="text-[10px] text-muted-foreground">
                Uses Application Default Credentials (ADC)
              </p>
              <code className="text-[10px] bg-muted px-1.5 py-0.5 rounded mt-1 inline-block">
                gcloud auth application-default login
              </code>
            </div>
            <div>
              {steps?.gcp_authenticated ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-300" />
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border p-4 flex items-center gap-4">
            <AWSLogo className="h-8 w-8 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium">Amazon Web Services</p>
              <p className="text-[10px] text-muted-foreground">
                Requires IAM Access Key (ReadOnlyAccess policy)
              </p>
              <a href="/settings" className="text-[10px] text-primary hover:underline mt-1 inline-block">
                Configure in Settings →
              </a>
            </div>
            <div>
              {steps?.aws_configured ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-300" />
              )}
            </div>
          </div>

          {steps?.cloud_provider && (
            <div className="rounded-lg bg-green-50 dark:bg-green-500/5 border border-green-200 dark:border-green-500/20 p-3 text-xs text-green-700 dark:text-green-300 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              At least one cloud provider is connected. You're ready to proceed!
            </div>
          )}

          <button onClick={refreshStatus} className="text-xs text-primary hover:underline">
            ↻ Refresh status
          </button>
        </div>
      ),
    },
    // Step 2: AI (optional) + Launch
    {
      title: "AI Code Cleaning (Optional)",
      subtitle: "Configure an AI provider to automatically clean generated Terraform code",
      content: (
        <div className="space-y-4 py-2">
          <div className="rounded-xl border border-border p-4 flex items-center gap-4">
            <BrainCircuit className="h-8 w-8 text-violet-500 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium">AI Provider</p>
              <p className="text-[10px] text-muted-foreground">
                Supports OpenAI, Anthropic, Google AI, Ollama, and more
              </p>
              <a href="/settings" className="text-[10px] text-primary hover:underline mt-1 inline-block">
                Configure in Settings →
              </a>
            </div>
            <div>
              {steps?.ai_configured ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <span className="text-[10px] text-muted-foreground bg-muted px-2 py-0.5 rounded">Optional</span>
              )}
            </div>
          </div>

          <div className="rounded-lg bg-muted/50 p-4 text-center space-y-2">
            <Rocket className="h-6 w-6 text-primary mx-auto" />
            <p className="text-sm font-medium">You're all set!</p>
            <p className="text-xs text-muted-foreground">
              Head to the Discover page to scan your first project.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-lg mx-4 rounded-2xl border border-border bg-card shadow-2xl overflow-hidden">
        {/* Dismiss button */}
        <button
          onClick={onDismiss}
          className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          aria-label="Dismiss wizard"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2 pt-6">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === step ? "w-6 bg-primary" : i < step ? "w-1.5 bg-primary/50" : "w-1.5 bg-muted"
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <div className="px-8 pt-6 pb-4">
          <h2 className="text-lg font-semibold text-center">{stepContent[step].title}</h2>
          <p className="text-xs text-muted-foreground text-center mt-1">{stepContent[step].subtitle}</p>
          <div className="mt-4">{stepContent[step].content}</div>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between px-8 py-4 border-t border-border/50">
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground disabled:opacity-0 transition-all"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </button>

          {step < totalSteps - 1 ? (
            <button
              onClick={() => { refreshStatus(); setStep(step + 1); }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all"
            >
              Next <ArrowRight className="h-3.5 w-3.5" />
            </button>
          ) : (
            <a
              href="/discover"
              onClick={onComplete}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all"
            >
              Start Discovering <Rocket className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
