"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import type { AuthStatus } from "@/lib/api";

export default function SettingsPage() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);

  useEffect(() => {
    apiClient.getAuthStatus().then(setAuth).catch(() => setAuth(null));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Configuration and credentials status.</p>
      </div>

      <div className="rounded-lg border bg-card p-6 space-y-4">
        <h3 className="text-sm font-medium">GCP Authentication</h3>
        {auth ? (
          <div className="space-y-2 text-sm">
            <p>
              <span className="text-muted-foreground">Status:</span>{" "}
              <span className={auth.authenticated ? "text-green-500" : "text-destructive"}>
                {auth.authenticated ? "Authenticated" : "Not Authenticated"}
              </span>
            </p>
            {auth.project && (
              <p>
                <span className="text-muted-foreground">Default Project:</span>{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{auth.project}</code>
              </p>
            )}
            {auth.account && (
              <p>
                <span className="text-muted-foreground">Account:</span>{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{auth.account}</code>
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Unable to check authentication status.</p>
        )}
      </div>

      <div className="rounded-lg border bg-card p-6 space-y-3">
        <h3 className="text-sm font-medium">Setup Instructions</h3>
        <div className="text-sm text-muted-foreground space-y-2">
          <p>To authenticate with GCP, run:</p>
          <code className="block rounded bg-muted px-3 py-2 text-xs">
            gcloud auth application-default login
          </code>
          <p>Or set a service account key:</p>
          <code className="block rounded bg-muted px-3 py-2 text-xs">
            export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
          </code>
        </div>
      </div>
    </div>
  );
}
