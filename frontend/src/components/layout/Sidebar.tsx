"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Search,
  Code,
  Settings,
  RefreshCw,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Discover", href: "/discover", icon: Search },
  { name: "Generate", href: "/generate", icon: Code },
  { name: "Drift Fix", href: "/drift", icon: RefreshCw },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-[260px] h-screen flex flex-col border-r border-gray-200/60 dark:border-white/[0.10] bg-white dark:bg-[#0a0a0a]">
      {/* Logo area */}
      <div className="px-5 py-5 flex items-center gap-2.5">
        <img src="/logo.png" alt="Terramorph" className="w-7 h-7 rounded-lg" />
        <span className="text-sm font-semibold tracking-tight text-gray-900 dark:text-white">
          Terramorph
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {navigation.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                active
                  ? "bg-gray-100 dark:bg-white/[0.06] text-gray-900 dark:text-white"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-white/[0.03]"
              }`}
            >
              <item.icon
                className={`w-4 h-4 ${
                  active
                    ? "text-indigo-500"
                    : "text-gray-400 dark:text-gray-500"
                }`}
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Bottom section */}
      <div className="px-3 py-4 border-t border-gray-100 dark:border-white/[0.04]">
        <div className="flex items-center gap-2.5 px-3 py-2">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-400 to-violet-400 flex items-center justify-center">
            <span className="text-[10px] font-medium text-white">TM</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-900 dark:text-gray-100 truncate">
              Self-hosted
            </p>
            <p className="text-[11px] text-gray-400">v1.0.0</p>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse-slow" aria-hidden="true" />
          </div>
        </div>
      </div>
    </aside>
  );
}
