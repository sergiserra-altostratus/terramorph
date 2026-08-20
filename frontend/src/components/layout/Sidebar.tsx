"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  LayoutDashboard,
  Search,
  Code,
  Settings,
  RefreshCw,
  Upload,
  Network,
  X,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Discover", href: "/discover", icon: Search },
  { name: "Generate", href: "/generate", icon: Code },
  { name: "Auto Import", href: "/auto-import", icon: Upload },
  { name: "Drift Fix", href: "/drift", icon: RefreshCw },
  { name: "State Graph", href: "/state-viz", icon: Network },
  { name: "Settings", href: "/settings", icon: Settings },
];

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
  const pathname = usePathname();

  useEffect(() => {
    if (mobileOpen && onMobileClose) onMobileClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const content = (
    <>
      {/* Logo */}
      <div className="px-4 py-4 flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="Terramorph" className="w-6 h-6 rounded" />
          <span className="text-sm font-medium tracking-tight">Terramorph</span>
        </div>
        {onMobileClose && (
          <button onClick={onMobileClose} className="lg:hidden p-1 rounded-md hover:bg-muted text-muted-foreground" aria-label="Close menu">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5" aria-label="Main navigation">
        {navigation.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[13px] transition-colors ${
                active
                  ? "text-foreground bg-muted font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              }`}
            >
              <item.icon className={`w-4 h-4 ${active ? "text-emerald-500" : ""}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-border">
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-xs text-muted-foreground">Self-hosted · v1.0</span>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop */}
      <aside className="hidden lg:flex w-56 h-screen flex-col border-r border-border bg-background">
        {content}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onMobileClose} aria-hidden="true" />
          <aside className="fixed inset-y-0 left-0 z-50 w-64 flex flex-col bg-background border-r border-border shadow-xl lg:hidden animate-slide-in-left">
            {content}
          </aside>
        </>
      )}
    </>
  );
}
