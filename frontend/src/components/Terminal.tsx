"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Terminal as TerminalIcon, Circle } from "lucide-react";

export interface TerminalLine {
  text: string;
  stream: "stdout" | "stderr";
  phase: string;
  timestamp: number;
}

interface TerminalProps {
  lines: TerminalLine[];
  isActive: boolean;
  currentPhase?: string;
  className?: string;
  maxHeight?: string;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

/**
 * Lightweight ANSI color code parser.
 * Supports basic colors (30-37, 90-97), bold (1), reset (0).
 */
function parseAnsiLine(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const ansiRegex = /\x1B\[([0-9;]*)m/g;

  let lastIndex = 0;
  let currentStyle: React.CSSProperties = {};
  let match: RegExpExecArray | null;

  const colorMap: Record<number, string> = {
    30: "#1e1e1e", 31: "#f87171", 32: "#4ade80", 33: "#fbbf24",
    34: "#60a5fa", 35: "#c084fc", 36: "#22d3ee", 37: "#e5e7eb",
    90: "#6b7280", 91: "#fca5a5", 92: "#86efac", 93: "#fde047",
    94: "#93c5fd", 95: "#d8b4fe", 96: "#67e8f9", 97: "#f9fafb",
  };

  while ((match = ansiRegex.exec(text)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      const segment = text.slice(lastIndex, match.index);
      if (segment) {
        parts.push(
          <span key={`${lastIndex}-text`} style={{ ...currentStyle }}>
            {segment}
          </span>
        );
      }
    }

    // Parse codes
    const codes = match[1].split(";").map(Number);
    for (const code of codes) {
      if (code === 0) {
        currentStyle = {};
      } else if (code === 1) {
        currentStyle = { ...currentStyle, fontWeight: "bold" };
      } else if (colorMap[code]) {
        currentStyle = { ...currentStyle, color: colorMap[code] };
      }
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    const remaining = text.slice(lastIndex);
    if (remaining) {
      parts.push(
        <span key={`${lastIndex}-rest`} style={{ ...currentStyle }}>
          {remaining}
        </span>
      );
    }
  }

  // If no ANSI found, return plain text
  if (parts.length === 0) {
    return [<span key="plain">{text}</span>];
  }

  return parts;
}

function formatElapsed(startTs: number): string {
  const elapsed = Math.floor((Date.now() / 1000) - startTs);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  if (mins > 0) return `${mins}m ${secs}s`;
  return `${secs}s`;
}

const phaseLabels: Record<string, string> = {
  init: "Init",
  plan: "Plan",
  fix: "AI Fix",
  verify: "Verify",
  done: "Done",
};

export default function Terminal({
  lines,
  isActive,
  currentPhase,
  className = "",
  maxHeight = "400px",
  collapsed = false,
  onToggleCollapse,
}: TerminalProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [elapsed, setElapsed] = useState("0s");

  // Auto-scroll when new lines arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines, autoScroll]);

  // Update elapsed time
  useEffect(() => {
    if (!isActive || lines.length === 0) return;
    const startTs = lines[0].timestamp;
    const interval = setInterval(() => {
      setElapsed(formatElapsed(startTs));
    }, 1000);
    return () => clearInterval(interval);
  }, [isActive, lines]);

  // Update elapsed on lines change when not active
  useEffect(() => {
    if (!isActive && lines.length > 0) {
      const startTs = lines[0].timestamp;
      const endTs = lines[lines.length - 1].timestamp;
      const secs = Math.floor(endTs - startTs);
      const mins = Math.floor(secs / 60);
      setElapsed(mins > 0 ? `${mins}m ${secs % 60}s` : `${secs}s`);
    }
  }, [isActive, lines]);

  // Detect manual scroll
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(atBottom);
  };

  const isPhaseHeader = (text: string) =>
    text.includes("═══") || text.startsWith("▶") || text.startsWith("✓");

  return (
    <div
      className={`rounded-md border border-border overflow-hidden transition-all duration-300 ${className}`}
      role="log"
      aria-label="Terraform command output terminal"
      aria-live="polite"
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-gray-700/50">
        <div className="flex items-center gap-3">
          <TerminalIcon className="h-3.5 w-3.5 text-gray-400" />
          <span className="text-xs font-medium text-gray-300">Terminal</span>
          {currentPhase && (
            <span className="inline-flex items-center gap-1.5 rounded-md bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-400">
              {isActive && <Circle className="h-1.5 w-1.5 fill-indigo-400 animate-pulse" />}
              {phaseLabels[currentPhase] || currentPhase}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-gray-500">{lines.length} lines</span>
          <span className="text-[10px] text-gray-500">{elapsed}</span>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="p-1 rounded hover:bg-gray-700/50 text-gray-400 hover:text-gray-200 transition-colors"
              aria-label={collapsed ? "Expand terminal" : "Collapse terminal"}
            >
              {collapsed ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
            </button>
          )}
        </div>
      </div>

      {/* Terminal body */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="bg-[#0d1117] overflow-y-auto overflow-x-auto text-xs leading-5 transition-all duration-300"
        style={{
          maxHeight: collapsed ? "0px" : maxHeight,
          padding: collapsed ? "0 1rem" : "0.75rem 1rem",
          opacity: collapsed ? 0 : 1,
          fontFamily: "'MesloLGS NF', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace",
        }}
        tabIndex={0}
        aria-label="Terminal output scroll area"
      >
        {lines.map((line, i) => {
          const isErr = line.stream === "stderr";
          const isHeader = isPhaseHeader(line.text);

          return (
            <div
              key={i}
              className={`whitespace-pre-wrap break-all ${
                isErr
                  ? "text-red-400"
                  : isHeader
                  ? "text-cyan-400 font-semibold"
                  : "text-gray-300"
              }`}
            >
              {parseAnsiLine(line.text)}
            </div>
          );
        })}

        {/* Blinking cursor */}
        {isActive && (
          <div className="inline-flex items-center mt-0.5">
            <span className="w-2 h-4 bg-gray-300 animate-pulse" />
          </div>
        )}

        {/* Empty state */}
        {lines.length === 0 && (
          <div className="text-gray-600 italic">Waiting for output...</div>
        )}
      </div>
    </div>
  );
}
