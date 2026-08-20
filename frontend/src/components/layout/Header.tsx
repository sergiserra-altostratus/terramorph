"use client";

import { Menu, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { apiClient } from "@/lib/api";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/discover": "Discover",
  "/generate": "Generate",
  "/auto-import": "Auto Import",
  "/drift": "Drift Fix",
  "/state-viz": "State Graph",
  "/settings": "Settings",
};

interface HeaderProps {
  onMenuToggle?: () => void;
}

export function Header({ onMenuToggle }: HeaderProps) {
  const { theme, setTheme } = useTheme();
  const [connected, setConnected] = useState<boolean | null>(null);
  const pathname = usePathname();

  const pageTitle = pageTitles[pathname] || "Terramorph";

  useEffect(() => {
    apiClient.getHealth().then(() => setConnected(true)).catch(() => setConnected(false));
  }, []);

  return (
    <header className="h-12 flex items-center justify-between px-4 lg:px-6 border-b border-border bg-background sticky top-0 z-30">
      <div className="flex items-center gap-3">
        {onMenuToggle && (
          <button onClick={onMenuToggle} className="lg:hidden p-1.5 -ml-1 rounded-md hover:bg-muted text-muted-foreground" aria-label="Open menu">
            <Menu className="h-4 w-4" />
          </button>
        )}
        <h2 className="text-sm font-medium">{pageTitle}</h2>
      </div>

      <div className="flex items-center gap-3">
        {/* Status */}
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full ${connected === true ? "bg-emerald-500" : connected === false ? "bg-red-400" : "bg-zinc-400"}`} />
          <span className="text-[11px] text-muted-foreground hidden sm:inline">
            {connected === true ? "Connected" : connected === false ? "Disconnected" : "..."}
          </span>
        </div>

        {/* Theme */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Toggle theme"
        >
          <Sun className="h-3.5 w-3.5 block dark:hidden" />
          <Moon className="h-3.5 w-3.5 hidden dark:block" />
        </button>
      </div>
    </header>
  );
}
