"use client";

import { Suspense, useCallback, useRef, useState, useEffect } from "react";
import {
  Network,
  Upload,
  FileText,
  Loader2,
  Trash2,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  resource_type: string | null;
}

interface GraphEdge {
  source: string;
  target: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_resources: number;
  total_data_sources: number;
}

// Node colors by type
const nodeColors: Record<string, { bg: string; border: string; text: string }> = {
  resource: { bg: "#818cf8", border: "#6366f1", text: "#ffffff" },
  data: { bg: "#34d399", border: "#10b981", text: "#ffffff" },
  module: { bg: "#f59e0b", border: "#d97706", text: "#ffffff" },
  var: { bg: "#94a3b8", border: "#64748b", text: "#ffffff" },
  output: { bg: "#f472b6", border: "#ec4899", text: "#ffffff" },
  provider: { bg: "#64748b", border: "#475569", text: "#ffffff" },
};

// Simple force-directed layout (no external deps)
function computeLayout(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number) {
  const positions: Record<string, { x: number; y: number }> = {};

  // Group nodes by resource_type for clustering
  const groups: Record<string, GraphNode[]> = {};
  nodes.forEach((n) => {
    const key = n.resource_type || n.type;
    if (!groups[key]) groups[key] = [];
    groups[key].push(n);
  });

  // Layout in a grid-like pattern with some randomness
  const groupKeys = Object.keys(groups);
  const cols = Math.ceil(Math.sqrt(groupKeys.length));
  const cellW = width / (cols + 1);
  const cellH = height / (Math.ceil(groupKeys.length / cols) + 1);

  groupKeys.forEach((groupKey, gi) => {
    const col = gi % cols;
    const row = Math.floor(gi / cols);
    const cx = cellW * (col + 1);
    const cy = cellH * (row + 1);

    groups[groupKey].forEach((node, ni) => {
      const angle = (2 * Math.PI * ni) / groups[groupKey].length;
      const radius = Math.min(cellW, cellH) * 0.3;
      positions[node.id] = {
        x: cx + Math.cos(angle) * radius * (groups[groupKey].length > 1 ? 1 : 0),
        y: cy + Math.sin(angle) * radius * (groups[groupKey].length > 1 ? 1 : 0),
      };
    });
  });

  return positions;
}

function StateVizContent() {
  const [files, setFiles] = useState<Record<string, string>>({});
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const processFiles = (fileList: FileList | File[]) => {
    const newFiles: Record<string, string> = { ...files };
    Array.from(fileList).forEach((file) => {
      if (file.name.endsWith(".tf")) {
        const reader = new FileReader();
        reader.onload = (e) => {
          newFiles[file.name] = e.target?.result as string;
          setFiles({ ...newFiles });
        };
        reader.readAsText(file);
      }
    });
  };

  const generateGraph = async () => {
    if (Object.keys(files).length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.request<GraphData>("/state/graph", {
        method: "POST",
        body: JSON.stringify({ tf_files: files, project_id: "" }),
      });
      setGraph(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate graph");
    } finally {
      setLoading(false);
    }
  };

  // SVG dimensions
  const svgWidth = 900;
  const svgHeight = 600;
  const positions = graph ? computeLayout(graph.nodes, graph.edges, svgWidth, svgHeight) : {};

  // Mouse handlers for pan
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) { setDragging(true); setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y }); }
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (dragging) { setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y }); }
  };
  const handleMouseUp = () => setDragging(false);

  // Get connected nodes for highlighting
  const connectedNodes = new Set<string>();
  if (hoveredNode && graph) {
    graph.edges.forEach((e) => {
      if (e.source === hoveredNode) connectedNodes.add(e.target);
      if (e.target === hoveredNode) connectedNodes.add(e.source);
    });
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-foreground">
          <Network className="h-4 w-4 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-semibold tracking-tight">State Visualization</h1>
          <p className="text-sm text-muted-foreground">
            Visualize Terraform resource dependencies as an interactive graph.
          </p>
        </div>
      </div>

      {/* Upload + Controls */}
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Upload panel */}
        <div className="lg:w-72 space-y-3">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); processFiles(e.dataTransfer.files); }}
            onClick={() => fileInputRef.current?.click()}
            className={`rounded-md border-2 border-dashed p-6 text-center cursor-pointer transition-all ${
              dragOver ? "border-violet-500 bg-violet-50 dark:bg-violet-500/10" : "border-gray-300 dark:border-white/10 hover:border-violet-400"
            }`}
          >
            <Upload className={`h-6 w-6 mx-auto mb-2 ${dragOver ? "text-violet-500" : "text-gray-400"}`} />
            <p className="text-xs font-medium text-gray-600 dark:text-gray-300">Drop .tf files</p>
            <input ref={fileInputRef} type="file" multiple accept=".tf" onChange={(e) => e.target.files && processFiles(e.target.files)} className="hidden" />
          </div>

          {/* File list */}
          {Object.keys(files).length > 0 && (
            <div className="space-y-1">
              {Object.keys(files).map((name) => (
                <div key={name} className="flex items-center justify-between px-2 py-1 rounded-lg bg-muted/30 text-xs">
                  <span className="font-mono truncate flex items-center gap-1.5"><FileText className="h-3 w-3 text-gray-400" />{name}</span>
                  <button onClick={() => { const u = { ...files }; delete u[name]; setFiles(u); }} className="text-gray-400 hover:text-red-500"><Trash2 className="h-3 w-3" /></button>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={generateGraph}
            disabled={loading || Object.keys(files).length === 0}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-foreground text-background text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:pointer-events-none"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Network className="h-4 w-4" />}
            {loading ? "Generating..." : "Generate Graph"}
          </button>

          {/* Stats */}
          {graph && (
            <div className="rounded-md border border-border bg-background p-3 space-y-1.5">
              <p className="text-[10px] font-semibold uppercase text-muted-foreground">Graph Stats</p>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Resources</span><span className="font-medium">{graph.total_resources}</span></div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Data Sources</span><span className="font-medium">{graph.total_data_sources}</span></div>
              <div className="flex justify-between text-xs"><span className="text-muted-foreground">Dependencies</span><span className="font-medium">{graph.edges.length}</span></div>
            </div>
          )}
        </div>

        {/* Graph area */}
        <div className="flex-1 rounded-md border border-border bg-white dark:bg-[#0d1117] overflow-hidden relative" style={{ minHeight: "500px" }}>
          {/* Zoom controls */}
          <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
            <button onClick={() => setZoom((z) => Math.min(z + 0.2, 3))} className="p-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors" aria-label="Zoom in"><ZoomIn className="h-3.5 w-3.5" /></button>
            <button onClick={() => setZoom((z) => Math.max(z - 0.2, 0.3))} className="p-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors" aria-label="Zoom out"><ZoomOut className="h-3.5 w-3.5" /></button>
            <button onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }} className="p-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors" aria-label="Reset view"><Maximize2 className="h-3.5 w-3.5" /></button>
          </div>

          {!graph && !loading && (
            <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
              Upload .tf files and click "Generate Graph" to visualize dependencies
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
            </div>
          )}

          {graph && graph.nodes.length > 0 && (
            <svg
              ref={svgRef}
              width="100%" height="100%"
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="cursor-grab active:cursor-grabbing"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Edges */}
                {graph.edges.map((edge, i) => {
                  const from = positions[edge.source];
                  const to = positions[edge.target];
                  if (!from || !to) return null;
                  const isHighlighted = hoveredNode && (edge.source === hoveredNode || edge.target === hoveredNode);
                  return (
                    <line
                      key={i}
                      x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                      stroke={isHighlighted ? "#8b5cf6" : "#475569"}
                      strokeWidth={isHighlighted ? 2 : 1}
                      strokeOpacity={hoveredNode && !isHighlighted ? 0.15 : 0.5}
                      markerEnd="url(#arrowhead)"
                    />
                  );
                })}

                {/* Arrow marker */}
                <defs>
                  <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                    <polygon points="0 0, 8 3, 0 6" fill="#475569" fillOpacity="0.6" />
                  </marker>
                </defs>

                {/* Nodes */}
                {graph.nodes.map((node) => {
                  const pos = positions[node.id];
                  if (!pos) return null;
                  const colors = nodeColors[node.type] || nodeColors.resource;
                  const isHovered = hoveredNode === node.id;
                  const isConnected = connectedNodes.has(node.id);
                  const dimmed = hoveredNode && !isHovered && !isConnected;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      onMouseEnter={() => setHoveredNode(node.id)}
                      onMouseLeave={() => setHoveredNode(null)}
                      className="cursor-pointer"
                      opacity={dimmed ? 0.2 : 1}
                    >
                      <rect
                        x={-55} y={-16} width={110} height={32} rx={6}
                        fill={colors.bg}
                        stroke={isHovered ? "#ffffff" : colors.border}
                        strokeWidth={isHovered ? 2 : 1}
                      />
                      <text
                        x={0} y={1}
                        textAnchor="middle" dominantBaseline="middle"
                        fill={colors.text}
                        fontSize={10}
                        fontFamily="ui-monospace, monospace"
                      >
                        {node.label.length > 14 ? node.label.slice(0, 13) + "…" : node.label}
                      </text>
                      {/* Type badge */}
                      <text
                        x={0} y={12}
                        textAnchor="middle"
                        fill={colors.text}
                        fontSize={7}
                        opacity={0.7}
                      >
                        {node.resource_type || node.type}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}

          {graph && graph.nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
              No resources found in the provided files.
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md border border-red-200 dark:border-red-500/20 bg-red-50 dark:bg-red-500/5 p-4">
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Legend */}
      {graph && (
        <div className="flex items-center gap-4 text-[10px]">
          <span className="text-muted-foreground font-medium">Legend:</span>
          {Object.entries(nodeColors).filter(([k]) => k === "resource" || k === "data" || k === "module").map(([type, colors]) => (
            <div key={type} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: colors.bg }} />
              <span className="capitalize text-muted-foreground">{type}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function StateVizPage() {
  return (
    <Suspense fallback={<div className="animate-pulse p-8 text-muted-foreground">Loading...</div>}>
      <StateVizContent />
    </Suspense>
  );
}
