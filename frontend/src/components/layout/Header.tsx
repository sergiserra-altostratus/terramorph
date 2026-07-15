"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { apiClient } from "@/lib/api";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/discover": "Discover",
  "/generate": "Generate",
  "/settings": "Settings",
};

export function Header() {
  const { theme, setTheme } = useTheme();
  const [connected, setConnected] = useState<boolean | null>(null);
  const pathname = usePathname();

  const pageTitle = pageTitles[pathname] || "Terramorph";

  useEffect(() => {
    apiClient
      .getHealth()
      .then(() => setConnected(true))
      .catch(() => setConnected(false));
  }, []);

  return (
    <header className="h-14 flex items-center justify-between px-6 lg:px-8 border-b border-gray-200/60 dark:border-white/[0.10] bg-white/80 dark:bg-[#0a0a0a]/80 backdrop-blur-xl sticky top-0 z-40">
      {/* Breadcrumb / Page title */}
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium text-gray-900 dark:text-white">
          {pageTitle}
        </h2>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Connection status */}
        <div className="flex items-center gap-2 rounded-lg px-2.5 py-1.5">
          <div
            className={`h-2 w-2 rounded-full transition-colors ${
              connected === true
                ? "bg-emerald-500"
                : connected === false
                ? "bg-rose-500"
                : "bg-amber-500 animate-pulse-slow"
            }`}
          />
          <span className="text-[11px] text-gray-500 dark:text-gray-400">
            {connected === true
              ? "Connected"
              : connected === false
              ? "Disconnected"
              : "Checking..."}
          </span>
        </div>

        {/* Theme toggle — refined */}
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/[0.06] transition-all duration-150"
          aria-label="Toggle theme"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all duration-200 dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all duration-200 dark:rotate-0 dark:scale-100" />
        </button>
      </div>
    </header>
  );
}
