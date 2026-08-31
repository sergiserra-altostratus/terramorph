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
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Discover", href: "/discover", icon: Search },
  { name: "Generate", href: "/generate", icon: Code },
  { name: "Drift Fix", href: "/drift", icon: RefreshCw },
  { type: "separator", label: "Tools" },
  { name: "Auto Import", href: "/auto-import", icon: Upload },
  { name: "State Graph", href: "/state-viz", icon: Network },
  { type: "separator", label: "System" },
  { name: "Settings", href: "/settings", icon: Settings },
] as const;

interface SidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Sidebar({ mobileOpen = false, onMobileClose, collapsed = false, onToggleCollapse }: SidebarProps) {
  const pathname = usePathname();

  useEffect(() => {
    if (mobileOpen && onMobileClose) onMobileClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  // Full sidebar content (expanded)
  const expandedContent = (
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
        {navigation.map((item, i) => {
          if ("type" in item && item.type === "separator") {
            return (
              <div key={item.label} className="pt-3 pb-1 px-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{item.label}</span>
              </div>
            );
          }
          if (!("href" in item)) return null;
          const active = isActive(item.href);
          return (
            <Link key={item.name} href={item.href} aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[13px] transition-colors ${
                active ? "text-foreground bg-muted font-medium" : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              }`}>
              <item.icon className={`w-4 h-4 flex-shrink-0 ${active ? "text-emerald-500" : ""}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-border">
        <div className="flex items-center justify-between px-2 py-1">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
            <span className="text-xs text-muted-foreground">Self-hosted · v1.0</span>
          </div>
          {onToggleCollapse && (
            <button onClick={onToggleCollapse} className="hidden lg:flex p-1 rounded-md hover:bg-muted text-muted-foreground" aria-label="Collapse sidebar">
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </>
  );

  // Collapsed sidebar content (icons only)
  const collapsedContent = (
    <>
      {/* Logo */}
      <div className="px-2 py-4 flex justify-center border-b border-border">
        <img src="/logo.png" alt="Terramorph" className="w-6 h-6 rounded" />
      </div>

      {/* Nav icons */}
      <nav className="flex-1 px-1.5 py-3 space-y-1" aria-label="Main navigation">
        {navigation.map((item, i) => {
          if ("type" in item && item.type === "separator") {
            return <div key={item.label} className="my-2 border-t border-border" />;
          }
          if (!("href" in item)) return null;
          const active = isActive(item.href);
          return (
            <Link key={item.name} href={item.href} aria-current={active ? "page" : undefined}
              title={item.name}
              className={`flex items-center justify-center p-2 rounded-md transition-colors ${
                active ? "text-foreground bg-muted" : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              }`}>
              <item.icon className={`w-4 h-4 ${active ? "text-emerald-500" : ""}`} />
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-1.5 py-3 border-t border-border flex flex-col items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-emerald-500" />
        {onToggleCollapse && (
          <button onClick={onToggleCollapse} className="p-1 rounded-md hover:bg-muted text-muted-foreground" aria-label="Expand sidebar">
            <PanelLeftOpen className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </>
  );

  return (
    <>
      {/* Desktop */}
      <aside className={`hidden lg:flex h-screen flex-col border-r border-border bg-background transition-all duration-200 ${collapsed ? "w-12" : "w-56"}`}>
        {collapsed ? collapsedContent : expandedContent}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onMobileClose} aria-hidden="true" />
          <aside className="fixed inset-y-0 left-0 z-50 w-64 flex flex-col bg-background border-r border-border shadow-xl lg:hidden animate-slide-in-left">
            {expandedContent}
          </aside>
        </>
      )}
    </>
  );
}
