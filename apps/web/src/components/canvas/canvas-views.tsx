"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Network,
  FolderTree,
  LayoutGrid,
  Cpu,
  FlaskConical,
  Lightbulb,
  Vote,
  Layers,
  Maximize2,
  ChevronRight,
  ChevronDown,
  FileCode,
  Folder,
  GripVertical,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Search,
  MoreHorizontal,
} from "lucide-react";
import { useCanvasState, useCanvasActions } from "@/hooks/use-canvas";
import { cn } from "@/lib/utils";
import type { FolderItem, CanvasNode, CanvasEdge, CanvasLayout } from "@/types/canvas";

/* ── Mode Toggle ──────────────────────────────────────────────── */

export function ModeToggle() {
  const { mode } = useCanvasState();
  const { setMode } = useCanvasActions();

  return (
    <div className="inline-flex items-center rounded-lg border border-inkos-cyan/10 bg-inkos-navy-800/40 p-[3px]">
      <button
        onClick={() => setMode("visual")}
        className={cn(
          "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
          mode === "visual"
            ? "bg-inkos-cyan/15 text-inkos-cyan shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        <Network className="h-3.5 w-3.5" />
        Visual
      </button>
      <button
        onClick={() => setMode("folder")}
        className={cn(
          "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
          mode === "folder"
            ? "bg-inkos-cyan/15 text-inkos-cyan shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        <FolderTree className="h-3.5 w-3.5" />
        Folder
      </button>
    </div>
  );
}

/* ── Layout Selector ──────────────────────────────────────────── */

const LAYOUT_OPTIONS: { value: CanvasLayout; label: string; icon: React.ElementType }[] = [
  { value: "smart", label: "Smart Auto", icon: Cpu },
  { value: "layered", label: "Layered", icon: LayoutGrid },
  { value: "hub-and-spoke", label: "Hub & Spoke", icon: Network },
  { value: "clustered", label: "Clustered", icon: Layers },
  { value: "linear", label: "Linear", icon: Maximize2 },
];

export function LayoutSelector() {
  const { layout } = useCanvasState();
  const { setLayout } = useCanvasActions();
  const [open, setOpen] = useState(false);

  const active = LAYOUT_OPTIONS.find((l) => l.value === layout) ?? LAYOUT_OPTIONS[0];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-800/40 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-all"
      >
        <active.icon className="h-3.5 w-3.5" />
        {active.label}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute right-0 top-full mt-1 z-50 w-40 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-900 shadow-xl overflow-hidden"
          >
            {LAYOUT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  setLayout(opt.value);
                  setOpen(false);
                }}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors",
                  layout === opt.value
                    ? "bg-inkos-cyan/10 text-inkos-cyan"
                    : "text-muted-foreground hover:bg-white/[0.03] hover:text-foreground",
                )}
              >
                <opt.icon className="h-3.5 w-3.5" />
                {opt.label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Canvas Toolbar ───────────────────────────────────────────── */

export function CanvasToolbar() {
  const { setNodes, setEdges } = useCanvasActions();

  const handleReset = useCallback(() => {
    setNodes([]);
    setEdges([]);
  }, [setNodes, setEdges]);

  return (
    <div className="flex items-center gap-2">
      <ModeToggle />
      <LayoutSelector />
      <div className="h-4 w-px bg-white/[0.06]" />
      <button
        onClick={handleReset}
        className="h-7 w-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"
        title="Reset view"
      >
        <RotateCcw className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

/* ── Prime Feature Quick-Access ───────────────────────────────── */

export function PrimeFeatureBar() {
  const features = [
    { label: "Simulate", icon: FlaskConical, href: "/simulations", color: "text-inkos-cyan" },
    { label: "Explain", icon: Lightbulb, href: "/explain", color: "text-inkos-cyan" },
    { label: "Proposals", icon: Vote, href: "/proposals", color: "text-amber-400" },
    { label: "Domains", icon: Layers, href: "/domains", color: "text-emerald-400" },
  ];

  return (
    <div className="flex items-center gap-1">
      {features.map((f) => (
        <a
          key={f.label}
          href={f.href}
          className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"
        >
          <f.icon className={cn("h-3.5 w-3.5", f.color)} />
          {f.label}
        </a>
      ))}
    </div>
  );
}

/* ── Mock Folder Data Generator ───────────────────────────────── */

function generateMockFolderTree(): FolderItem {
  return {
    name: "root",
    path: "/",
    type: "directory",
    children: [
      {
        name: "agents",
        path: "/agents",
        type: "directory",
        children: [
          {
            name: "contract_analyst",
            path: "/agents/contract_analyst",
            type: "directory",
            children: [
              { name: "role.md", path: "/agents/contract_analyst/role.md", type: "file", size: 1200 },
              { name: "goals.md", path: "/agents/contract_analyst/goals.md", type: "file", size: 800 },
              { name: "tools", path: "/agents/contract_analyst/tools", type: "directory", children: [] },
            ],
          },
          {
            name: "compliance_checker",
            path: "/agents/compliance_checker",
            type: "directory",
            children: [
              { name: "role.md", path: "/agents/compliance_checker/role.md", type: "file", size: 1100 },
            ],
          },
        ],
      },
      {
        name: "skills",
        path: "/skills",
        type: "directory",
        children: [
          { name: "contract_analysis.py", path: "/skills/contract_analysis.py", type: "file", size: 3400 },
          { name: "risk_scoring.py", path: "/skills/risk_scoring.py", type: "file", size: 2100 },
        ],
      },
      {
        name: "workflows",
        path: "/workflows",
        type: "directory",
        children: [
          {
            name: "full_contract_review",
            path: "/workflows/full_contract_review",
            type: "directory",
            children: [
              { name: "workflow.json", path: "/workflows/full_contract_review/workflow.json", type: "file", size: 4500 },
              { name: "example_inputs", path: "/workflows/full_contract_review/example_inputs", type: "directory", children: [] },
            ],
          },
        ],
      },
      {
        name: "templates",
        path: "/templates",
        type: "directory",
        children: [
          { name: "analyze_contract_prompt.md", path: "/templates/analyze_contract_prompt.md", type: "file", size: 900 },
        ],
      },
      {
        name: "config",
        path: "/config",
        type: "directory",
        children: [
          { name: "domain_config.json", path: "/config/domain_config.json", type: "file", size: 600 },
        ],
      },
      {
        name: "data_sources",
        path: "/data_sources",
        type: "directory",
        children: [],
      },
      { name: "README.md", path: "/README.md", type: "file", size: 1500 },
    ],
  };
}

/* ── Folder Tree View ─────────────────────────────────────────── */

function FolderTreeItem({
  item,
  depth = 0,
}: {
  item: FolderItem;
  depth?: number;
}) {
  const { expandedFolders, folderPath } = useCanvasState();
  const { toggleFolder, setFolderPath } = useCanvasActions();
  const isExpanded = expandedFolders.has(item.path);
  const isSelected = folderPath === item.path;
  const hasChildren = item.children && item.children.length > 0;

  return (
    <div>
      <button
        onClick={() => {
          if (item.type === "directory" && hasChildren) {
            toggleFolder(item.path);
          }
          setFolderPath(item.path);
        }}
        className={cn(
          "w-full flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-all",
          isSelected
            ? "bg-inkos-cyan/10 text-inkos-cyan"
            : "text-muted-foreground hover:text-foreground hover:bg-white/[0.03]",
        )}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {item.type === "directory" && hasChildren && (
          <span className="shrink-0">
            {isExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </span>
        )}
        {item.type === "directory" ? (
          <Folder className={cn("h-3.5 w-3.5 shrink-0", isSelected ? "text-inkos-cyan" : "text-amber-400/70")} />
        ) : (
          <FileCode className="h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
        )}
        <span className="truncate">{item.name}</span>
        {item.size !== undefined && (
          <span className="ml-auto text-[10px] text-muted-foreground/40 tabular-nums">
            {(item.size / 1024).toFixed(1)} KB
          </span>
        )}
      </button>
      <AnimatePresence>
        {isExpanded && hasChildren && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            {item.children!.map((child) => (
              <FolderTreeItem key={child.path} item={child} depth={depth + 1} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function FolderTreeView() {
  const tree = generateMockFolderTree();
  const { expandAll, collapseAll } = useCanvasActions();
  const [search, setSearch] = useState("");

  const filterTree = (item: FolderItem, query: string): FolderItem | null => {
    if (!query) return item;
    const match = item.name.toLowerCase().includes(query.toLowerCase());
    const filteredChildren = item.children
      ?.map((c) => filterTree(c, query))
      .filter(Boolean) as FolderItem[] | undefined;
    if (match || (filteredChildren && filteredChildren.length > 0)) {
      return { ...item, children: filteredChildren };
    }
    return null;
  };

  const filteredTree = search ? filterTree(tree, search) : tree;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[0.04]">
        <div className="flex-1 flex items-center gap-1.5 rounded-md border border-inkos-cyan/8 bg-inkos-navy-800/30 px-2 py-1">
          <Search className="h-3 w-3 text-muted-foreground/50" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search files..."
            className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground/40 outline-none"
          />
        </div>
        <button
          onClick={expandAll}
          className="text-[10px] px-2 py-1 rounded border border-inkos-cyan/10 text-muted-foreground hover:text-foreground transition-all"
        >
          Expand
        </button>
        <button
          onClick={collapseAll}
          className="text-[10px] px-2 py-1 rounded border border-inkos-cyan/10 text-muted-foreground hover:text-foreground transition-all"
        >
          Collapse
        </button>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-auto p-2">
        {filteredTree && <FolderTreeItem item={filteredTree} />}
      </div>
    </div>
  );
}

/* ── Visual Canvas View ───────────────────────────────────────── */

function NodeCard({
  node,
  onSelect,
}: {
  node: CanvasNode;
  onSelect: (id: string) => void;
}) {
  const { selectedNodeId } = useCanvasState();
  const isSelected = selectedNodeId === node.id;

  const statusColors: Record<string, string> = {
    active: "border-emerald-400/30 text-emerald-400",
    idle: "border-amber-400/30 text-amber-400",
    error: "border-red-400/30 text-red-400",
    offline: "border-white/[0.06] text-muted-foreground",
    building: "border-inkos-cyan/30 text-inkos-cyan animate-pulse",
  };

  const typeIcons: Record<string, React.ReactNode> = {
    agent: <Cpu className="h-4 w-4" />,
    skill: <FileCode className="h-4 w-4" />,
    workflow: <Layers className="h-4 w-4" />,
    domain: <Network className="h-4 w-4" />,
    browser: <Search className="h-4 w-4" />,
    terminal: <FolderTree className="h-4 w-4" />,
    plugin: <MoreHorizontal className="h-4 w-4" />,
    group: <LayoutGrid className="h-4 w-4" />,
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      onClick={() => onSelect(node.id)}
      className={cn(
        "absolute cursor-pointer rounded-xl border p-3 transition-all duration-200",
        isSelected
          ? "border-inkos-cyan/40 bg-inkos-cyan/8 shadow-lg shadow-inkos-cyan/5"
          : "border-white/[0.06] bg-card/80 hover:border-inkos-cyan/20 hover:bg-card",
      )}
      style={{
        left: node.x,
        top: node.y,
        width: node.width,
        height: node.height,
      }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-inkos-cyan">{typeIcons[node.type]}</span>
        <span className="text-xs font-semibold truncate">{node.label}</span>
        <span
          className={cn(
            "ml-auto text-[9px] font-mono uppercase px-1 py-0.5 rounded border",
            statusColors[node.status],
          )}
        >
          {node.status}
        </span>
      </div>
      {node.description && (
        <p className="text-[10px] text-muted-foreground line-clamp-2 leading-relaxed">
          {node.description}
        </p>
      )}
      {node.folderPath && (
        <p className="text-[9px] text-muted-foreground/50 mt-1 font-mono truncate">
          {node.folderPath}
        </p>
      )}
    </motion.div>
  );
}

function EdgeLine({ edge, nodes }: { edge: CanvasEdge; nodes: CanvasNode[] }) {
  const source = nodes.find((n) => n.id === edge.source);
  const target = nodes.find((n) => n.id === edge.target);
  if (!source || !target) return null;

  const sx = source.x + source.width / 2;
  const sy = source.y + source.height / 2;
  const tx = target.x + target.width / 2;
  const ty = target.y + target.height / 2;

  const edgeColors: Record<string, string> = {
    dependency: "rgba(34, 211, 238, 0.25)",
    flow: "rgba(103, 232, 249, 0.2)",
    data: "rgba(16, 185, 129, 0.2)",
    control: "rgba(245, 158, 11, 0.2)",
    group: "rgba(255, 255, 255, 0.06)",
  };

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      style={{ width: "100%", height: "100%" }}
    >
      <line
        x1={sx}
        y1={sy}
        x2={tx}
        y2={ty}
        stroke={edgeColors[edge.type] ?? edgeColors.dependency}
        strokeWidth={1.5}
        strokeDasharray={edge.type === "flow" ? "4 4" : undefined}
      />
      {edge.label && (
        <text
          x={(sx + tx) / 2}
          y={(sy + ty) / 2 - 4}
          fill="rgba(123, 139, 168, 0.7)"
          fontSize={9}
          textAnchor="middle"
        >
          {edge.label}
        </text>
      )}
    </svg>
  );
}

function generateMockNodes(): CanvasNode[] {
  return [
    { id: "domain-1", type: "domain", label: "Legal Research Domain", status: "active", x: 350, y: 40, width: 180, height: 70, description: "Contract analysis and compliance checking domain", metadata: {}, folderPath: "/" },
    { id: "agent-1", type: "agent", label: "Contract Analyst", status: "active", x: 120, y: 160, width: 160, height: 80, description: "Analyzes legal contracts for risks and obligations", metadata: {}, folderPath: "/agents/contract_analyst" },
    { id: "agent-2", type: "agent", label: "Compliance Checker", status: "idle", x: 360, y: 160, width: 160, height: 80, description: "Validates regulatory compliance", metadata: {}, folderPath: "/agents/compliance_checker" },
    { id: "agent-3", type: "agent", label: "Risk Scorer", status: "active", x: 600, y: 160, width: 160, height: 80, description: "Scores contract risk profiles", metadata: {}, folderPath: "/agents/risk_scorer" },
    { id: "skill-1", type: "skill", label: "contract_analysis.py", status: "active", x: 120, y: 300, width: 160, height: 60, description: "Contract parsing and clause extraction", metadata: {}, folderPath: "/skills/contract_analysis.py" },
    { id: "skill-2", type: "skill", label: "risk_scoring.py", status: "active", x: 360, y: 300, width: 160, height: 60, description: "Risk assessment algorithms", metadata: {}, folderPath: "/skills/risk_scoring.py" },
    { id: "skill-3", type: "skill", label: "compliance_check.py", status: "idle", x: 600, y: 300, width: 160, height: 60, description: "Regulatory compliance validation", metadata: {}, folderPath: "/skills/compliance_check.py" },
    { id: "wf-1", type: "workflow", label: "Full Contract Review", status: "active", x: 360, y: 420, width: 180, height: 70, description: "End-to-end contract review workflow", metadata: {}, folderPath: "/workflows/full_contract_review" },
  ];
}

function generateMockEdges(): CanvasEdge[] {
  return [
    { id: "e1", source: "domain-1", target: "agent-1", type: "group", metadata: {} },
    { id: "e2", source: "domain-1", target: "agent-2", type: "group", metadata: {} },
    { id: "e3", source: "domain-1", target: "agent-3", type: "group", metadata: {} },
    { id: "e4", source: "agent-1", target: "skill-1", type: "dependency", metadata: {} },
    { id: "e5", source: "agent-2", target: "skill-3", type: "dependency", metadata: {} },
    { id: "e6", source: "agent-3", target: "skill-2", type: "dependency", metadata: {} },
    { id: "e7", source: "agent-1", target: "wf-1", type: "flow", label: "inputs", metadata: {} },
    { id: "e8", source: "agent-2", target: "wf-1", type: "flow", label: "validates", metadata: {} },
    { id: "e9", source: "agent-3", target: "wf-1", type: "flow", label: "scores", metadata: {} },
    { id: "e10", source: "skill-1", target: "wf-1", type: "data", metadata: {} },
    { id: "e11", source: "skill-2", target: "wf-1", type: "data", metadata: {} },
  ];
}

export function VisualCanvasView() {
  const { nodes, edges, selectedNodeId } = useCanvasState();
  const { setNodes, setEdges, selectNode } = useCanvasActions();
  const [scale, setScale] = useState(1);

  // Initialize mock data if empty
  useState(() => {
    if (nodes.length === 0) {
      setNodes(generateMockNodes());
      setEdges(generateMockEdges());
    }
  });

  // Use a safer initialization pattern
  const initialized = nodes.length > 0;

  return (
    <div className="relative flex-1 overflow-hidden bg-background">
      {/* Grid background */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(34, 211, 238, 0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(34, 211, 238, 0.5) 1px, transparent 1px)
          `,
          backgroundSize: `${24 * scale}px ${24 * scale}px`,
        }}
      />

      {/* Canvas content */}
      <div
        className="absolute inset-0"
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "top left",
        }}
      >
        {/* Edges */}
        {edges.map((edge) => (
          <EdgeLine key={edge.id} edge={edge} nodes={nodes} />
        ))}

        {/* Nodes */}
        {nodes.map((node) => (
          <NodeCard key={node.id} node={node} onSelect={selectNode} />
        ))}
      </div>

      {/* Zoom controls */}
      <div className="absolute bottom-4 right-4 flex items-center gap-1 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-900/90 p-1">
        <button
          onClick={() => setScale((s) => Math.max(0.5, s - 0.1))}
          className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"
        >
          <ZoomOut className="h-3.5 w-3.5" />
        </button>
        <span className="text-[10px] font-mono text-muted-foreground w-10 text-center">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={() => setScale((s) => Math.min(2, s + 0.1))}
          className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"
        >
          <ZoomIn className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Selected node info */}
      <AnimatePresence>
        {selectedNodeId && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="absolute top-4 right-4 w-64 glass rounded-xl border border-inkos-cyan/10 p-4"
          >
            <SelectedNodePanel nodeId={selectedNodeId} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Initialize button if empty */}
      {!initialized && (
        <div className="absolute inset-0 flex items-center justify-center">
          <button
            onClick={() => {
              setNodes(generateMockNodes());
              setEdges(generateMockEdges());
            }}
            className="flex items-center gap-2 rounded-lg border border-inkos-cyan/20 bg-inkos-cyan/10 px-4 py-2 text-sm text-inkos-cyan hover:bg-inkos-cyan/20 transition-all"
          >
            <Network className="h-4 w-4" />
            Load Demo Canvas
          </button>
        </div>
      )}
    </div>
  );
}

function SelectedNodePanel({ nodeId }: { nodeId: string }) {
  const { nodes } = useCanvasState();
  const { selectNode } = useCanvasActions();
  const node = nodes.find((n) => n.id === nodeId);
  if (!node) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Node Details
        </span>
        <button
          onClick={() => selectNode(null)}
          className="text-muted-foreground hover:text-foreground"
        >
          ✕
        </button>
      </div>
      <div className="space-y-2">
        <div>
          <span className="text-[10px] text-muted-foreground uppercase">Label</span>
          <p className="text-sm font-medium">{node.label}</p>
        </div>
        <div>
          <span className="text-[10px] text-muted-foreground uppercase">Type</span>
          <p className="text-xs">{node.type}</p>
        </div>
        <div>
          <span className="text-[10px] text-muted-foreground uppercase">Status</span>
          <p className="text-xs">{node.status}</p>
        </div>
        {node.folderPath && (
          <div>
            <span className="text-[10px] text-muted-foreground uppercase">Path</span>
            <p className="text-[10px] font-mono text-muted-foreground">{node.folderPath}</p>
          </div>
        )}
        {node.description && (
          <div>
            <span className="text-[10px] text-muted-foreground uppercase">Description</span>
            <p className="text-xs text-muted-foreground leading-relaxed">{node.description}</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Folder Thinking Mode Panel ───────────────────────────────── */

export function FolderThinkingPanel() {
  return (
    <div className="w-72 border-l border-white/[0.04] bg-inkos-navy-900/50 flex flex-col">
      <div className="px-4 py-3 border-b border-white/[0.04]">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <FolderTree className="h-3.5 w-3.5" />
          Folder Thinking Mode
        </h3>
        <p className="text-[10px] text-muted-foreground/60 mt-1">
          Prime navigates and reasons about the domain using the canonical folder tree.
        </p>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        <div className="rounded-lg border border-inkos-cyan/8 bg-inkos-cyan/[0.02] p-3">
          <p className="text-[10px] text-muted-foreground uppercase mb-1">Current Path</p>
          <p className="text-xs font-mono text-inkos-cyan">/agents/contract_analyst</p>
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-muted-foreground uppercase">Prime Actions</p>
          {[
            { action: "folder_navigate", target: "/skills", time: "2s ago" },
            { action: "folder_read", target: "/config/domain_config.json", time: "5s ago" },
            { action: "folder_search", target: "*.py", time: "12s ago" },
            { action: "file_modified", target: "/agents/contract_analyst/role.md", time: "1m ago" },
          ].map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs hover:bg-white/[0.02] transition-colors"
            >
              <GripVertical className="h-3 w-3 text-muted-foreground/30" />
              <span className="text-inkos-cyan font-mono text-[10px]">{item.action}</span>
              <span className="truncate text-muted-foreground">{item.target}</span>
              <span className="ml-auto text-[10px] text-muted-foreground/40">{item.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
