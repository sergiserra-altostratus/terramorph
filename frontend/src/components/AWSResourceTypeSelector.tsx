"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Server,
  Network,
  Database,
  Boxes,
  Shield,
  Globe,
  CheckSquare,
  Square,
  MinusSquare,
} from "lucide-react";
import {
  AWS_RESOURCE_CATEGORIES,
  ALL_AWS_RESOURCE_TYPES,
  AWS_RESOURCE_TYPE_LABELS,
} from "@/types";
import type { AWSResourceType } from "@/types";

const CATEGORY_META: Record<string, { icon: React.ElementType; accent: string; accentBg: string; accentText: string; accentBorder: string }> = {
  "Compute": { icon: Server, accent: "from-orange-500 to-orange-600", accentBg: "bg-orange-500/10", accentText: "text-orange-400", accentBorder: "border-orange-400/30" },
  "Networking": { icon: Network, accent: "from-blue-500 to-blue-600", accentBg: "bg-blue-500/10", accentText: "text-blue-400", accentBorder: "border-blue-400/30" },
  "Storage & Databases": { icon: Database, accent: "from-amber-500 to-amber-600", accentBg: "bg-amber-500/10", accentText: "text-amber-400", accentBorder: "border-amber-400/30" },
  "Containers & Serverless": { icon: Boxes, accent: "from-violet-500 to-violet-600", accentBg: "bg-violet-500/10", accentText: "text-violet-400", accentBorder: "border-violet-400/30" },
  "Security & IAM": { icon: Shield, accent: "from-red-500 to-red-600", accentBg: "bg-red-500/10", accentText: "text-red-400", accentBorder: "border-red-400/30" },
  "DNS": { icon: Globe, accent: "from-emerald-500 to-emerald-600", accentBg: "bg-emerald-500/10", accentText: "text-emerald-400", accentBorder: "border-emerald-400/30" },
};

interface AWSResourceTypeSelectorProps {
  selectedTypes: string[];
  onChange: (types: string[]) => void;
  disabled?: boolean;
}

export function AWSResourceTypeSelector({ selectedTypes, onChange, disabled }: AWSResourceTypeSelectorProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const totalCount = ALL_AWS_RESOURCE_TYPES.length;
  const selectedCount = selectedTypes.length;
  const allSelected = selectedCount === totalCount;
  const noneSelected = selectedCount === 0;

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      next.has(category) ? next.delete(category) : next.add(category);
      return next;
    });
  };

  const handleSelectAll = () => onChange([...ALL_AWS_RESOURCE_TYPES]);
  const handleDeselectAll = () => onChange([]);

  const handleSelectCategory = (category: string) => {
    const types = AWS_RESOURCE_CATEGORIES[category];
    const merged = new Set([...selectedTypes, ...types]);
    onChange([...merged]);
  };
  const handleDeselectCategory = (category: string) => {
    const categoryTypes = new Set(AWS_RESOURCE_CATEGORIES[category] as string[]);
    onChange(selectedTypes.filter((t) => !categoryTypes.has(t)));
  };

  const toggleType = (type: string) => {
    onChange(
      selectedTypes.includes(type)
        ? selectedTypes.filter((t) => t !== type)
        : [...selectedTypes, type]
    );
  };

  const getCategoryState = (category: string) => {
    const types = AWS_RESOURCE_CATEGORIES[category] as string[];
    const selected = types.filter((t) => selectedTypes.includes(t));
    return { selected: selected.length, total: types.length, allSelected: selected.length === types.length, noneSelected: selected.length === 0, partial: selected.length > 0 && selected.length < types.length };
  };

  return (
    <div className="space-y-4">
      {/* Global Toolbar */}
      <div className="flex items-center justify-between rounded-xl border border-border bg-muted/30 backdrop-blur-sm px-4 py-3">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold">AWS Resource Types</h3>
          <span className="inline-flex items-center rounded-full bg-orange-500/10 border border-orange-500/30 px-2.5 py-0.5 text-xs font-medium text-orange-600 dark:text-orange-400">
            {selectedCount}/{totalCount}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleSelectAll} disabled={allSelected || disabled} className="text-xs font-medium text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors px-2 py-1 rounded hover:bg-accent">
            Select All
          </button>
          <span className="text-muted-foreground/30">|</span>
          <button onClick={handleDeselectAll} disabled={noneSelected || disabled} className="text-xs font-medium text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors px-2 py-1 rounded hover:bg-accent">
            Deselect All
          </button>
        </div>
      </div>

      {/* Categories Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
        {Object.entries(AWS_RESOURCE_CATEGORIES).map(([category, types]) => {
          const meta = CATEGORY_META[category] || CATEGORY_META["Compute"];
          const Icon = meta.icon;
          const isExpanded = expandedCategories.has(category);
          const state = getCategoryState(category);

          return (
            <div key={category} className="relative overflow-hidden rounded-xl border border-border bg-card/50 backdrop-blur-sm transition-all duration-200 ease-in-out hover:border-primary/20">
              <div className={`absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b ${meta.accent}`} />
              <div
                role="button" tabIndex={0} aria-expanded={isExpanded}
                className={`flex items-center justify-between px-4 py-3 cursor-pointer select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring ${isExpanded ? "rounded-t-xl" : "rounded-xl"}`}
                onClick={() => toggleCategory(category)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleCategory(category); } }}
              >
                <div className="flex items-center gap-3">
                  <div className={`flex items-center justify-center w-8 h-8 rounded-lg ${meta.accentBg}`}>
                    <Icon className={`w-4 h-4 ${meta.accentText}`} />
                  </div>
                  <span className="text-sm font-medium">{category}</span>
                  <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
                    state.allSelected ? "bg-green-500/15 text-green-600 dark:text-green-400 border border-green-500/30"
                    : state.partial ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                    : "bg-muted text-muted-foreground border border-border"
                  }`}>
                    {state.selected}/{state.total}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); state.allSelected ? handleDeselectCategory(category) : handleSelectCategory(category); }}
                    disabled={disabled}
                    className="p-1 rounded hover:bg-accent transition-colors"
                    aria-label={state.allSelected ? `Deselect all in ${category}` : `Select all in ${category}`}
                  >
                    {state.allSelected ? <CheckSquare className="w-4 h-4 text-green-500" /> : state.partial ? <MinusSquare className="w-4 h-4 text-amber-500" /> : <Square className="w-4 h-4 text-muted-foreground" />}
                  </button>
                  <div className="text-muted-foreground transition-transform duration-200">
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="px-4 pb-3 pt-0">
                  <div className="border-t border-border/50 pt-3">
                    <div className="flex flex-wrap gap-2">
                      {types.map((type) => {
                        const isSelected = selectedTypes.includes(type);
                        return (
                          <button
                            key={type} onClick={() => toggleType(type)} disabled={disabled} aria-pressed={isSelected}
                            className={`inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-medium transition-all duration-150 border ${
                              isSelected
                                ? `${meta.accentBg} ${meta.accentText} ${meta.accentBorder} shadow-sm`
                                : "bg-background text-muted-foreground border-border hover:bg-accent hover:text-foreground hover:border-primary/20"
                            }`}
                          >
                            {AWS_RESOURCE_TYPE_LABELS[type as AWSResourceType]}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
