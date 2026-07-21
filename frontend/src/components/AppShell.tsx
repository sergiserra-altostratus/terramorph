"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { OnboardingWizard } from "@/components/OnboardingWizard";

const ONBOARDING_DISMISSED_KEY = "terramorph_onboarding_dismissed";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    // Skip if user already dismissed
    if (typeof window !== "undefined" && localStorage.getItem(ONBOARDING_DISMISSED_KEY)) {
      return;
    }

    // Check if onboarding is needed
    apiClient.request<any>("/onboarding/status")
      .then((data) => {
        if (data.onboarding_needed) {
          setShowOnboarding(true);
        }
      })
      .catch(() => {});
  }, []);

  const handleComplete = () => {
    setShowOnboarding(false);
    localStorage.setItem(ONBOARDING_DISMISSED_KEY, "true");
  };

  const handleDismiss = () => {
    setShowOnboarding(false);
    localStorage.setItem(ONBOARDING_DISMISSED_KEY, "true");
  };

  return (
    <>
      {children}
      {showOnboarding && (
        <OnboardingWizard onComplete={handleComplete} onDismiss={handleDismiss} />
      )}
    </>
  );
}
