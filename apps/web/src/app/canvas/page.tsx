"use client";

import { useState, useEffect, useCallback, useMemo, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Network, Layers, X, Cpu, FlaskConical, Lightbulb, Users, History, Zap,
  Terminal, Monitor, Puzzle, Search, ZoomIn, ZoomOut, RotateCcw,
  ChevronRight, ChevronDown, Folder, FileCode, GitBranch, Sparkles,
  AlertTriangle, ArrowRight, Activity, Eye, EyeOff, LayoutGrid, Send,
  Loader2, Shield, Plus, Database, FileText, FolderTree, RefreshCw,
  Upload, ArrowLeft, Globe, Bug,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { CanvasNode, CanvasEdge, CanvasLayout, FolderItem } from "@/types/canvas";
import type {
  CopilotSuggestion, NLEditResult, SimulationMetric, TapeEventEntry,
  CanvasVersion, SwarmMode, FolderTreeNodeAPI, FolderTreeAPIResponse,
} from "@/types/canvas-v5";

type CanvasViewMode = "visual" | "folder";

/* ═══════════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════════ */

interface NodeTypeDef {
  id: string;
  label: string;
  type: string;
  description: string;
  icon: React.ElementType;
  color: string;
}

const NODE_TYPES: NodeTypeDef[] = [
  { id: "agent", label: "Agent", type: "agent", description: "Autonomous agent with tools", icon: Cpu, color: "#06b6d4" },
  { id: "skill", label: "Skill", type: "skill", description: "Reusable capability", icon: FileCode, color: "#10b981" },
  { id: "workflow", label: "Workflow", type: "workflow", description: "Pipeline or process", icon: GitBranch, color: "#f59e0b" },
  { id: "browser", label: "Browser Node", type: "browser", description: "Web browser integration", icon: Monitor, color: "#3b82f6" },
  { id: "terminal", label: "Terminal", type: "terminal", description: "TUI / PTY shell", icon: Terminal, color: "#16a34a" },
  { id: "plugin", label: "Plugin Node", type: "plugin", description: "External tool via Plugin SDK", icon: Puzzle, color: "#a855f7" },
  { id: "file_browser", label: "File Browser", type: "file_browser", description: "File system navigator", icon: Folder, color: "#f97316" },
  { id: "data_source", label: "Data Source", type: "data_source", description: "External data source", icon: Database, color: "#64748b" },
  { id: "template", label: "Template", type: "template", description: "Template document", icon: FileText, color: "#8b5cf6" },
];

interface DomainInfo {
  domain_id: string;
  domain_name: string;
  status?: string;
}

/* ═══════════════════════════════════════════════════════════════════
   Main Page
   ═══════════════════════════════════════════════════════════════════ */

export default function CanvasPage() {
  return (
    <Suspense
      fallback={<div className="flex flex-1 items-center justify-center min-h-screen"><div className="text-sm text-muted-foreground">Loading canvas...</div></div>}
    >
      <CanvasPageContent />
    </Suspense>
  );
}

function CanvasPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const urlDomainId = searchParams.get("domain_id");
  const isNewlyCreated = searchParams.get("from_creation") === "true";

  // Domain selection
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(urlDomainId);
  const [showDomainPicker, setShowDomainPicker] = useState(!urlDomainId);

  // Core canvas state
  const [viewMode, setViewMode] = useState<CanvasViewMode>("visual");
  const [layout, setLayout] = useState<CanvasLayout>("smart");
  const [canvasNodes, setCanvasNodes] = useState<CanvasNode[]>([]);
  const [canvasEdges, setCanvasEdges] = useState<CanvasEdge[]>([]);
  const [canvasLoaded, setCanvasLoaded] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [error, setError] = useState<string | null>(null);

  // V5 features
  const [showSimulationOverlay, setShowSimulationOverlay] = useState(false);
  const [showTapeOverlay, setShowTapeOverlay] = useState(false);
  const [showCopilot, setShowCopilot] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showNLEditor, setShowNLEditor] = useState(false);
  const [nlInput, setNlInput] = useState("");
  const [nlProcessing, setNlProcessing] = useState(false);
  const [nlLastResult, setNlLastResult] = useState<NLEditResult | null>(null);
  const [copilotSuggestions, setCopilotSuggestions] = useState<CopilotSuggestion[]>([]);
  const [simulationMetrics, setSimulationMetrics] = useState<Record<string, Record<string, SimulationMetric>>>({});
  const [tapeEvents, setTapeEvents] = useState<TapeEventEntry[]>([]);
  const [versions, setVersions] = useState<CanvasVersion[]>([]);
  const [showBanner, setShowBanner] = useState(isNewlyCreated);
  const [bootstrapping, setBootstrapping] = useState(false);

  // Folder tree
  const [folderTree, setFolderTree] = useState<FolderTreeAPIResponse | null>(null);

  // Drag state
  const [draggedNodeType, setDraggedNodeType] = useState<NodeTypeDef | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const domainId = selectedDomainId;

  // Load available domains
  useEffect(() => {
    async function fetchDomains() {
      try {
        const res = await fetch("/api/canvas/domains");
        if (res.ok) {
          const data = await res.json();
          setDomains(data.domain_ids?.map((id: string) => ({ domain_id: id, domain_name: id })) ?? []);
        }
      } catch { /* use empty list */ }
    }
    fetchDomains();
  }, []);

  // Auto-dismiss banner
  useEffect(() => {
    if (isNewlyCreated) {
      const timer = setTimeout(() => setShowBanner(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [isNewlyCreated]);

  // Load canvas when domain selected
  useEffect(() => {
    if (!domainId) { setCanvasLoaded(true); return; }
    async function fetchCanvas() {
      setError(null);
      setCanvasLoaded(false);
      try {
        const res = await fetch(`/api/canvas/${encodeURIComponent(domainId ?? "")}`);
        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          if (res.status === 404) {
            // Canvas doesn't exist -- try to bootstrap from blueprint
            await bootstrapCanvas();
            return;
          }
          throw new Error(errData?.detail || `Failed to load canvas: ${res.status}`);
        }
        const data = await res.json();
        setCanvasNodes(data.nodes ?? []);
        setCanvasEdges(data.edges ?? []);
        setCanvasLoaded(true);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to load canvas";
        setError(msg);
        setCanvasNodes([]);
        setCanvasEdges([]);
        setCanvasLoaded(true);
      }
    }
    fetchCanvas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domainId]);

  // Bootstrap canvas from domain blueprint
  const bootstrapCanvas = useCallback(async () => {
    if (!domainId) return;
    setBootstrapping(true);
    try {
      const res = await fetch(`/api/canvas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain_id: domainId, domain_name: domainId, layout: "smart", bootstrap_from_blueprint: true }),
      });
      if (res.ok) {
        const data = await res.json();
        setCanvasNodes(data.nodes ?? []);
        setCanvasEdges(data.edges ?? []);
        setCanvasLoaded(true);
        return;
      }
      // Fallback: create empty canvas
      const emptyRes = await fetch(`/api/canvas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domain_id: domainId, domain_name: domainId, layout: "smart", bootstrap_from_blueprint: false }),
      });
      if (emptyRes.ok) {
        const data = await emptyRes.json();
        setCanvasNodes(data.nodes ?? []);
        setCanvasEdges(data.edges ?? []);
        setCanvasLoaded(true);
      } else {
        throw new Error("Failed to create canvas");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to bootstrap canvas");
      setCanvasNodes([]);
      setCanvasEdges([]);
      setCanvasLoaded(true);
    }
    setBootstrapping(false);
  }, [domainId]);

  // Load folder tree for folder mode
  const loadFolderTree = useCallback(async () => {
    if (!domainId) return;
    try {
      const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}/folder-tree`);
      if (res.ok) {
        const data = await res.json();
        setFolderTree(data);
      }
    } catch { /* silent */ }
  }, [domainId]);

  // Fetch copilot suggestions
  const fetchCopilotSuggestions = useCallback(async () => {
    if (!domainId) return;
    try {
      const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}/copilot`);
      if (res.ok) { const data = await res.json(); setCopilotSuggestions(data.suggestions ?? []); return; }
    } catch { /* silent */ }
    setCopilotSuggestions([]);
  }, [domainId]);

  // Fetch overlays
  const fetchSimulationOverlay = useCallback(async () => {
    if (!domainId) return;
    try { const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}/simulation-overlay`); if (res.ok) { const data = await res.json(); setSimulationMetrics(data.overlay ?? {}); return; } } catch { /* silent */ }
    setSimulationMetrics({});
  }, [domainId]);

  const fetchTapeOverlay = useCallback(async () => {
    if (!domainId) return;
    try { const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}/tape-overlay?limit=20`); if (res.ok) { const data = await res.json(); setTapeEvents(data.events ?? []); return; } } catch { /* silent */ }
    setTapeEvents([]);
  }, [domainId]);

  const fetchVersions = useCallback(async () => {
    if (!domainId) return;
    try { const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}/versions`); if (res.ok) { const data = await res.json(); setVersions(data.versions ?? []); return; } } catch { /* silent */ }
    setVersions([]);
  }, [domainId]);

  // Add node via API
  const addNode = useCallback(async (nodeType: string, label: string, x: number, y: number) => {
    if (!domainId) return false;
    try {
      const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}/nodes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: `node-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, node_type: nodeType, label, x, y, width: 180, height: 60, metadata: {} }),
      });
      if (res.ok) {
        const canvasRes = await fetch(`/api/canvas/${encodeURIComponent(domainId)}`);
        if (canvasRes.ok) { const d = await canvasRes.json(); setCanvasNodes(d.nodes ?? []); setCanvasEdges(d.edges ?? []); }
        return true;
      }
      return false;
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to add node"); return false; }
  }, [domainId]);

  // NL edit handler
  const handleNLSubmit = useCallback(async () => {
    if (!nlInput.trim() || !domainId) return;
    setNlProcessing(true);
    try {
      const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}/nl-edit`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: nlInput }),
      });
      if (res.ok) {
        const data = await res.json();
        setNlLastResult(data);
        setNlInput("");
        const canvasRes = await fetch(`/api/canvas/${encodeURIComponent(domainId)}`);
        if (canvasRes.ok) { const cd = await canvasRes.json(); setCanvasNodes(cd.nodes ?? []); setCanvasEdges(cd.edges ?? []); }
      }
    } catch { setNlLastResult({ edit_id: "error", instruction: nlInput, edit_type: "compound", confidence: 0, applied: false, changes: [], error: "Failed to apply edit" }); }
    setNlProcessing(false);
  }, [nlInput, domainId]);

  // Swarm handler
  const handleSwarm = useCallback(async (mode: SwarmMode) => {
    if (!domainId) return;
    const task = mode === "quick" ? "Optimize layout" : "Reorganize domain structure";
    try { await fetch(`/api/canvas/${encodeURIComponent(domainId)}/swarm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task, mode }) }); } catch { /* silent */ }
  }, [domainId]);

  // Drag handlers
  const handleDragStart = useCallback((e: React.DragEvent, nodeType: NodeTypeDef) => {
    setDraggedNodeType(nodeType);
    e.dataTransfer.setData("application/json", JSON.stringify(nodeType));
    e.dataTransfer.effectAllowed = "copy";
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; setIsDraggingOver(true); }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => { if (e.relatedTarget && !(e.currentTarget as Node).contains(e.relatedTarget as Node)) setIsDraggingOver(false); }, []);
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;
    let nt: NodeTypeDef | null = draggedNodeType;
    if (!nt) { try { nt = JSON.parse(e.dataTransfer.getData("application/json")); } catch { /* ignore */ } }
    if (nt) { await addNode(nt.type, nt.label, x - 90, y - 30); setDraggedNodeType(null); }
  }, [draggedNodeType, addNode, scale]);

  // Context menu
  const [contextMenu, setContextMenu] = useState<{ visible: boolean; x: number; y: number; items: { label: string; action: () => void; icon?: React.ElementType }[] } | null>(null);
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;
    setContextMenu({
      visible: true, x: e.clientX, y: e.clientY,
      items: [
        { label: "Add Agent", action: () => addNode("agent", "New Agent", x, y), icon: Cpu },
        { label: "Add Skill", action: () => addNode("skill", "New Skill", x, y), icon: FileCode },
        { label: "Add Workflow", action: () => addNode("workflow", "New Workflow", x, y), icon: GitBranch },
        { label: "Add Browser Node", action: () => addNode("browser", "Browser", x, y), icon: Monitor },
        { label: "Add Terminal Node", action: () => addNode("terminal", "Terminal", x, y), icon: Terminal },
        { label: "Add Plugin Node", action: () => addNode("plugin", "Plugin", x, y), icon: Puzzle },
      ],
    });
  }, [addNode, scale]);

  useEffect(() => { const h = () => setContextMenu(null); if (contextMenu?.visible) { window.addEventListener("click", h); return () => window.removeEventListener("click", h); } }, [contextMenu?.visible]);

  // Overlays auto-fetch
  useEffect(() => { if (showSimulationOverlay) fetchSimulationOverlay(); }, [showSimulationOverlay, fetchSimulationOverlay]);
  useEffect(() => { if (showTapeOverlay) fetchTapeOverlay(); }, [showTapeOverlay, fetchTapeOverlay]);
  useEffect(() => { if (showCopilot) fetchCopilotSuggestions(); }, [showCopilot, fetchCopilotSuggestions]);
  useEffect(() => { if (showVersionHistory) fetchVersions(); }, [showVersionHistory, fetchVersions]);
  useEffect(() => { if (viewMode === "folder") loadFolderTree(); }, [viewMode, loadFolderTree]);

  const selectedNode = useMemo(() => canvasNodes.find((n) => n.id === selectedNodeId), [canvasNodes, selectedNodeId]);
  const hasNodes = canvasNodes.length > 0;

  /* ═══ Domain Picker ═══ */
  if (!domainId) {
    return (
      <div className="flex flex-col flex-1 min-h-0 page-transition">
        <DomainPicker domains={domains} onSelect={(id) => { setSelectedDomainId(id); setShowDomainPicker(false); }} />
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 page-transition">
      {/* ═══ Header ═══ */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="shrink-0 border-b border-white/[0.04] bg-background/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3">
            <button onClick={() => { setSelectedDomainId(null); setCanvasLoaded(false); }} className="h-9 w-9 rounded-lg bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center hover:bg-inkos-cyan/15 transition-all">
              <Network className="h-5 w-5 text-inkos-cyan" />
            </button>
            <div>
              <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
                <span className="text-inkos-cyan text-glow-cyan">Domain</span>
                <span className="text-foreground">Canvas</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-inkos-purple/30 text-inkos-purple bg-inkos-purple/5">v5</span>
              </h1>
              <button onClick={() => setSelectedDomainId(null)} className="text-xs text-muted-foreground hover:text-inkos-cyan transition-colors">
                {domainId} <ArrowLeft className="h-3 w-3 inline" />
              </button>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-1">
            <FeatureToggle icon={Activity} label="Sim" active={showSimulationOverlay} onClick={() => setShowSimulationOverlay(!showSimulationOverlay)} color="text-emerald-400" />
            <FeatureToggle icon={Zap} label="Tape" active={showTapeOverlay} onClick={() => setShowTapeOverlay(!showTapeOverlay)} color="text-amber-400" />
            <FeatureToggle icon={Sparkles} label="Co-Pilot" active={showCopilot} onClick={() => setShowCopilot(!showCopilot)} color="text-inkos-purple" />
            <FeatureToggle icon={History} label="Versions" active={showVersionHistory} onClick={() => setShowVersionHistory(!showVersionHistory)} color="text-inkos-cyan" />
            <FeatureToggle icon={Sparkles} label="NL Edit" active={showNLEditor} onClick={() => setShowNLEditor(!showNLEditor)} color="text-pink-400" />
            <div className="h-4 w-px bg-white/[0.06] mx-1" />
            <SwarmButton mode="quick" onClick={() => handleSwarm("quick")} />
            <SwarmButton mode="governed" onClick={() => handleSwarm("governed")} />
          </div>

          <div className="flex items-center gap-3">
            <LayoutSelector layout={layout} onChange={setLayout} />
            <ViewModeToggle mode={viewMode} onChange={(m) => setViewMode(m)} />
          </div>
        </div>
      </motion.div>

      {/* ═══ Banner ═══ */}
      <AnimatePresence>
        {showBanner && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="shrink-0 overflow-hidden">
            <div className="flex items-center justify-between px-4 sm:px-6 py-2 bg-emerald-500/8 border-b border-emerald-500/15">
              <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /><span className="text-xs font-medium text-emerald-300">Canvas v5 ready -- visual development environment with Co-Pilot, Swarms, and AetherGit versioning</span></div>
              <button onClick={() => setShowBanner(false)} className="rounded-md p-1 text-emerald-400/60 hover:text-emerald-300 transition-colors"><X className="h-3.5 w-3.5" /></button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ Workspace ═══ */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {viewMode === "visual" ? (
          <>
            {/* Node Palette */}
            <NodePalette nodeTypes={NODE_TYPES} onDragStart={handleDragStart} />

            {/* Canvas */}
            <div className={cn("relative flex-1 overflow-hidden bg-background", isDraggingOver && "ring-2 ring-inkos-cyan/50 ring-inset")} onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop} onContextMenu={handleContextMenu}>
              <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: `linear-gradient(rgba(34, 211, 238, 0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(34, 211, 238, 0.5) 1px, transparent 1px)`, backgroundSize: `${24 * scale}px ${24 * scale}px` }} />
              <div className="absolute inset-0" style={{ transform: `scale(${scale})`, transformOrigin: "top left" }}>
                {canvasEdges.map((edge) => (<EdgeLine key={edge.id} edge={edge} nodes={canvasNodes} />))}
                {showTapeOverlay && tapeEvents.slice(0, 10).map((event, i) => (<TapeParticle key={event.event_id} event={event} nodes={canvasNodes} index={i} />))}
                {canvasNodes.map((node) => (<NodeCardV5 key={node.id} node={node} isSelected={selectedNodeId === node.id} onSelect={setSelectedNodeId} simulationMetrics={showSimulationOverlay ? simulationMetrics[node.id] : undefined} />))}
              </div>

              {/* Empty state */}
              {!bootstrapping && canvasLoaded && !hasNodes && !error && <EmptyCanvasState domainId={domainId} onBootstrap={bootstrapCanvas} />}

              {/* Loading state */}
              {bootstrapping && <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm"><div className="flex items-center gap-3"><Loader2 className="h-5 w-5 animate-spin text-inkos-cyan" /><span className="text-sm text-muted-foreground">Bootstrapping canvas from domain blueprint...</span></div></div>}

              {/* Error state */}
              {error && <div className="absolute inset-0 flex items-center justify-center"><div className="glass rounded-xl border border-red-500/20 p-6 max-w-md text-center"><AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-3" /><p className="text-sm text-red-300 mb-4">{error}</p><button onClick={bootstrapCanvas} className="h-8 px-4 rounded-lg bg-inkos-cyan/20 border border-inkos-cyan/30 text-inkos-cyan text-xs font-medium hover:bg-inkos-cyan/30 transition-all"><RefreshCw className="h-3.5 w-3.5 inline mr-1.5" />Retry</button></div></div>}

              {/* Zoom controls */}
              <div className="absolute bottom-4 right-4 flex items-center gap-1 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-900/90 backdrop-blur-sm p-1">
                <button onClick={() => setScale((s) => Math.max(0.5, s - 0.1))} className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"><ZoomOut className="h-3.5 w-3.5" /></button>
                <span className="text-[10px] font-mono text-muted-foreground w-10 text-center">{Math.round(scale * 100)}%</span>
                <button onClick={() => setScale((s) => Math.min(2, s + 0.1))} className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"><ZoomIn className="h-3.5 w-3.5" /></button>
                <div className="w-px h-4 bg-white/[0.06] mx-1" />
                <button onClick={() => { setScale(1); setSelectedNodeId(null); }} className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all" title="Reset view"><RotateCcw className="h-3.5 w-3.5" /></button>
              </div>

              {/* NL Edit bar */}
              {showNLEditor && (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="absolute bottom-16 left-4 right-4 max-w-2xl mx-auto">
                  <div className="glass rounded-xl border border-inkos-purple/20 p-3 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-inkos-purple shrink-0" />
                    <input type="text" value={nlInput} onChange={(e) => setNlInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleNLSubmit()} placeholder='Natural language edit — "Move the domain node to the center"' className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 outline-none" disabled={nlProcessing} />
                    <button onClick={handleNLSubmit} disabled={nlProcessing || !nlInput.trim()} className="shrink-0 h-8 px-3 rounded-lg bg-inkos-purple/20 border border-inkos-purple/30 text-inkos-purple text-xs font-medium hover:bg-inkos-purple/30 transition-all disabled:opacity-30">
                      {nlProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                  {nlLastResult && (
                    <div className={cn("mt-1 text-xs px-3 py-1.5 rounded-lg text-center", nlLastResult.applied ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/15" : "bg-red-500/10 text-red-300 border border-red-500/15")}>
                      {nlLastResult.applied ? `Applied: ${nlLastResult.edit_type} (${Math.round(nlLastResult.confidence * 100)}% confidence)` : `Failed: ${nlLastResult.error || "Could not parse instruction"}`}
                    </div>
                  )}
                </motion.div>
              )}

              {/* Context Menu */}
              {contextMenu?.visible && <ContextMenuComponent menu={contextMenu} onClose={() => setContextMenu(null)} />}
            </div>

            {/* Right panel */}
            <div className="w-80 border-l border-white/[0.04] bg-inkos-navy-900/50 flex flex-col overflow-hidden">
              <div className="shrink-0 flex border-b border-white/[0.04]">
                <PanelTab icon={Users} label="Details" active={!showCopilot && !showVersionHistory} onClick={() => { setShowCopilot(false); setShowVersionHistory(false); }} />
                <PanelTab icon={Sparkles} label="Co-Pilot" active={showCopilot} onClick={() => { setShowCopilot(true); setShowVersionHistory(false); }} />
                <PanelTab icon={History} label="Versions" active={showVersionHistory} onClick={() => { setShowVersionHistory(true); setShowCopilot(false); }} />
              </div>
              <div className="flex-1 overflow-auto">
                {showCopilot ? <CopilotPanel suggestions={copilotSuggestions} domainId={domainId || ""} /> : showVersionHistory ? <VersionPanel versions={versions} domainId={domainId || ""} /> : selectedNode ? <NodeDetailsPanel node={selectedNode} metrics={simulationMetrics[selectedNode.id]} /> : <EmptyPanel />}
              </div>
            </div>
          </>
        ) : (
          <FolderModeView folderTree={folderTree} domainId={domainId || ""} onRefresh={loadFolderTree} onSyncFromTree={async () => { if (!domainId) return; try { await fetch(`/api/canvas/${encodeURIComponent(domainId)}/sync-from-tree`, { method: "POST" }); const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}`); if (res.ok) { const d = await res.json(); setCanvasNodes(d.nodes ?? []); setCanvasEdges(d.edges ?? []); } } catch { /* silent */ } }} />
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Domain Picker
   ═══════════════════════════════════════════════════════════════════ */

function DomainPicker({ domains, onSelect }: { domains: DomainInfo[]; onSelect: (id: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-lg w-full">
        <div className="text-center mb-8">
          <div className="h-16 w-16 rounded-2xl bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center mx-auto mb-4">
            <Network className="h-8 w-8 text-inkos-cyan" />
          </div>
          <h1 className="text-2xl font-bold mb-2"><span className="text-inkos-cyan">Domain</span> Canvas</h1>
          <p className="text-sm text-muted-foreground">Select a domain to open its visual canvas, or create one from the Domains page.</p>
        </div>
        {domains.length > 0 ? (
          <div className="space-y-2">
            {domains.map((d) => (
              <button key={d.domain_id} onClick={() => onSelect(d.domain_id)} className="w-full flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.01] p-4 hover:bg-white/[0.03] hover:border-inkos-cyan/20 transition-all group">
                <div className="h-10 w-10 rounded-lg bg-inkos-cyan/8 flex items-center justify-center"><Globe className="h-5 w-5 text-inkos-cyan" /></div>
                <div className="flex-1 text-left"><p className="text-sm font-medium">{d.domain_name}</p><p className="text-[10px] text-muted-foreground font-mono">{d.domain_id}</p></div>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-inkos-cyan transition-colors" />
              </button>
            ))}
          </div>
        ) : (
          <div className="text-center py-8"><p className="text-sm text-muted-foreground">No canvases found. Create a domain first from the <a href="/domains" className="text-inkos-cyan hover:underline">Domains</a> page.</p></div>
        )}
      </motion.div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Empty Canvas State
   ═══════════════════════════════════════════════════════════════════ */

function EmptyCanvasState({ domainId, onBootstrap }: { domainId: string; onBootstrap: () => void }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div className="pointer-events-auto text-center max-w-md">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass rounded-2xl border border-inkos-cyan/15 p-8">
          <FolderTree className="h-12 w-12 text-inkos-cyan/30 mx-auto mb-4" />
          <h2 className="text-lg font-semibold mb-2">Empty Canvas</h2>
          <p className="text-sm text-muted-foreground mb-6">This domain has no canvas nodes yet. You can bootstrap from the domain blueprint, or drag nodes from the palette to get started.</p>
          <div className="flex items-center justify-center gap-3">
            <button onClick={onBootstrap} className="h-9 px-4 rounded-lg bg-inkos-cyan/20 border border-inkos-cyan/30 text-inkos-cyan text-xs font-medium hover:bg-inkos-cyan/30 transition-all">
              <Upload className="h-3.5 w-3.5 inline mr-1.5" />Bootstrap from Blueprint
            </button>
            <button onClick={() => {}} className="h-9 px-4 rounded-lg bg-white/[0.03] border border-white/[0.08] text-muted-foreground text-xs font-medium hover:text-foreground hover:bg-white/[0.05] transition-all">
              <Plus className="h-3.5 w-3.5 inline mr-1.5" />Drag Nodes to Start
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Folder Mode View -- Real folder tree rendering
   ═══════════════════════════════════════════════════════════════════ */

function FolderModeView({ folderTree, domainId, onRefresh, onSyncFromTree }: { folderTree: FolderTreeAPIResponse | null; domainId: string; onRefresh: () => void; onSyncFromTree: () => void }) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  // Auto-expand root on load
  useEffect(() => { if (folderTree) { setExpandedPaths(new Set([folderTree.root_path])); } }, [folderTree]);

  const toggleExpand = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path); else next.add(path);
      return next;
    });
  }, []);

  // Build tree structure from flat node list
  const nodesByPath = useMemo(() => {
    if (!folderTree) return new Map<string, FolderTreeNodeAPI>();
    const map = new Map<string, FolderTreeNodeAPI>();
    for (const n of folderTree.nodes) map.set(n.path, n);
    return map;
  }, [folderTree]);

  const renderNode = useCallback((path: string, depth: number) => {
    const node = nodesByPath.get(path);
    if (!node) return null;
    const isDir = node.node_type === "directory";
    const isExpanded = expandedPaths.has(path);
    const isSelected = selectedPath === path;
    const indent = depth * 16;

    return (
      <div key={path}>
        <button
          onClick={() => { if (isDir) toggleExpand(path); setSelectedPath(path); }}
          className={cn("w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-white/[0.03] transition-colors", isSelected && "bg-inkos-cyan/8 text-inkos-cyan")}
          style={{ paddingLeft: `${12 + indent}px` }}
        >
          {isDir ? (
            isExpanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          ) : (
            <span className="w-3.5" />
          )}
          {isDir ? (
            <Folder className={cn("h-4 w-4 shrink-0", isExpanded ? "text-inkos-cyan" : "text-muted-foreground")} />
          ) : (
            <FileCode className="h-4 w-4 shrink-0 text-emerald-400" />
          )}
          <span className="truncate">{node.name}</span>
          {isDir && node.children.length > 0 && <span className="ml-auto text-[9px] text-muted-foreground/50">{node.children.length}</span>}
        </button>
        {isDir && isExpanded && node.children.map((childPath) => renderNode(childPath, depth + 1))}
      </div>
    );
  }, [nodesByPath, expandedPaths, selectedPath, toggleExpand]);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="px-4 py-2 border-b border-white/[0.04] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-3.5 w-3.5 text-inkos-cyan" />
          <span className="text-xs font-medium text-muted-foreground">Folder Tree View</span>
          <span className="text-[10px] text-muted-foreground/50 ml-2">Source of truth</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onSyncFromTree} className="h-7 px-2 rounded-md text-[10px] font-medium text-inkos-cyan border border-inkos-cyan/15 hover:bg-inkos-cyan/5 transition-all">
            <RefreshCw className="h-3 w-3 inline mr-1" />Sync to Canvas
          </button>
          <button onClick={onRefresh} className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"><RefreshCw className="h-3 w-3" /></button>
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-auto py-2">
        {folderTree ? (
          <>
            {renderNode(folderTree.root_path, 0)}
            {selectedPath && (() => {
              const node = nodesByPath.get(selectedPath);
              if (!node || !node.content) return null;
              return (
                <div className="mx-3 mt-3 rounded-lg border border-white/[0.06] bg-white/[0.01] p-3">
                  <p className="text-[10px] font-mono text-muted-foreground mb-1">{selectedPath}</p>
                  <pre className="text-[10px] text-foreground/80 whitespace-pre-wrap font-mono leading-relaxed max-h-60 overflow-auto">{node.content}</pre>
                </div>
              );
            })()}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FolderTree className="h-8 w-8 text-muted-foreground/20 mb-3" />
            <p className="text-xs text-muted-foreground/50">No folder tree found for this domain</p>
            <p className="text-[10px] text-muted-foreground/30 mt-1">Create a domain from the Domains page to generate one</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Sub-Components
   ═══════════════════════════════════════════════════════════════════ */

function CheckCircle2({ className }: { className?: string }) { return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.94-9.14" /><path d="m9 11 3 3L22 4" /></svg>; }

function FeatureToggle({ icon: Icon, label, active, onClick, color }: { icon: React.ElementType; label: string; active: boolean; onClick: () => void; color: string }) {
  return (
    <button onClick={onClick} className={cn("flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-all", active ? `${color} bg-white/[0.05] border border-white/[0.08]` : "text-muted-foreground hover:text-foreground border border-transparent")}>
      <Icon className="h-3.5 w-3.5" /><span className="hidden lg:inline">{label}</span>
    </button>
  );
}

function SwarmButton({ mode, onClick }: { mode: SwarmMode; onClick: () => void }) {
  const isQuick = mode === "quick";
  return (
    <button onClick={onClick} className={cn("flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all", isQuick ? "text-inkos-cyan border border-inkos-cyan/15 hover:bg-inkos-cyan/5" : "text-amber-400 border border-amber-400/15 hover:bg-amber-400/5")}>
      {isQuick ? <Zap className="h-3.5 w-3.5" /> : <Shield className="h-3.5 w-3.5" />}
      <span className="hidden lg:inline">{isQuick ? "Quick" : "Governed"}</span>
    </button>
  );
}

function ViewModeToggle({ mode, onChange }: { mode: CanvasViewMode; onChange: (m: CanvasViewMode) => void }) {
  return (
    <div className="inline-flex items-center rounded-lg border border-inkos-cyan/10 bg-inkos-navy-800/40 p-[3px]">
      <button onClick={() => onChange("visual")} className={cn("flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all", mode === "visual" ? "bg-inkos-cyan/15 text-inkos-cyan shadow-sm" : "text-muted-foreground hover:text-foreground")}><Network className="h-3.5 w-3.5" />Visual</button>
      <button onClick={() => onChange("folder")} className={cn("flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all", mode === "folder" ? "bg-inkos-cyan/15 text-inkos-cyan shadow-sm" : "text-muted-foreground hover:text-foreground")}><Layers className="h-3.5 w-3.5" />Folder</button>
    </div>
  );
}

function LayoutSelector({ layout, onChange }: { layout: CanvasLayout; onChange: (l: CanvasLayout) => void }) {
  const options: { value: CanvasLayout; label: string; icon: React.ElementType }[] = [
    { value: "smart", label: "Smart Auto", icon: Cpu },
    { value: "layered", label: "Layered", icon: LayoutGrid },
    { value: "hub-and-spoke", label: "Hub & Spoke", icon: Network },
    { value: "clustered", label: "Clustered", icon: Layers },
    { value: "linear", label: "Linear", icon: ArrowRight },
  ];
  return (
    <div className="relative group">
      <button className="flex items-center gap-1.5 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-800/40 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-all">
        {(() => { const a = options.find((o) => o.value === layout) ?? options[0]; return <><a.icon className="h-3.5 w-3.5" />{a.label}</>; })()}
      </button>
      <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-900 shadow-xl overflow-hidden hidden group-hover:block">
        {options.map((opt) => (<button key={opt.value} onClick={() => onChange(opt.value)} className={cn("w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors", layout === opt.value ? "bg-inkos-cyan/10 text-inkos-cyan" : "text-muted-foreground hover:bg-white/[0.03] hover:text-foreground")}><opt.icon className="h-3.5 w-3.5" />{opt.label}</button>))}
      </div>
    </div>
  );
}

function PanelTab({ icon: Icon, label, active, onClick }: { icon: React.ElementType; label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={cn("flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-all border-b-2", active ? "text-inkos-cyan border-inkos-cyan" : "text-muted-foreground border-transparent hover:text-foreground")}>
      <Icon className="h-3.5 w-3.5" />{label}
    </button>
  );
}

/* -- Node Card -- */
const TYPE_ICONS: Record<string, React.ReactNode> = { agent: <Cpu className="h-4 w-4" />, skill: <FileCode className="h-4 w-4" />, workflow: <GitBranch className="h-4 w-4" />, domain: <Network className="h-4 w-4" />, browser: <Monitor className="h-4 w-4" />, terminal: <Terminal className="h-4 w-4" />, plugin: <Puzzle className="h-4 w-4" />, custom: <Puzzle className="h-4 w-4" /> };
const TYPE_COLORS: Record<string, string> = { agent: "border-cyan-400/30 text-cyan-400", skill: "border-emerald-400/30 text-emerald-400", workflow: "border-amber-400/30 text-amber-400", domain: "border-indigo-400/30 text-indigo-400", browser: "border-blue-400/30 text-blue-400", terminal: "border-green-400/30 text-green-400", plugin: "border-purple-400/30 text-purple-400", custom: "border-slate-400/30 text-slate-400" };

function NodeCardV5({ node, isSelected, onSelect, simulationMetrics }: { node: CanvasNode; isSelected: boolean; onSelect: (id: string) => void; simulationMetrics?: Record<string, SimulationMetric> }) {
  const typeKey = node.type || "custom";
  const iconEl = TYPE_ICONS[typeKey] ?? TYPE_ICONS.custom;
  const colorClass = TYPE_COLORS[typeKey] ?? TYPE_COLORS.custom;
  const worstStatus = simulationMetrics ? Object.values(simulationMetrics).reduce<string>((w, m) => { if (m.status === "critical") return "critical"; if (m.status === "warning" && w !== "critical") return "warning"; return w; }, "normal") : "normal";
  const statusBorderClass = worstStatus === "critical" ? "border-red-500/50 shadow-red-500/10" : worstStatus === "warning" ? "border-amber-500/40 shadow-amber-500/5" : "";

  return (
    <motion.div layout initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} whileHover={{ scale: 1.02 }} onClick={() => onSelect(node.id)}
      className={cn("absolute cursor-pointer rounded-xl border p-3 transition-all duration-200", isSelected ? "border-inkos-cyan/40 bg-inkos-cyan/8 shadow-lg shadow-inkos-cyan/5" : "border-white/[0.06] bg-card/80 hover:border-inkos-cyan/20", statusBorderClass && `shadow-md ${statusBorderClass}`)}
      style={{ left: node.x, top: node.y, width: node.width, height: node.height }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-inkos-cyan">{iconEl}</span>
        <span className="text-xs font-semibold truncate">{node.label}</span>
        <span className={cn("ml-auto text-[9px] font-mono uppercase px-1 py-0.5 rounded border", colorClass)}>{typeKey}</span>
      </div>
      {node.description != null && <p className="text-[10px] text-muted-foreground line-clamp-2 leading-relaxed">{node.description}</p>}
      {simulationMetrics && (
        <div className="flex items-center gap-1 mt-1.5">
          {Object.entries(simulationMetrics).slice(0, 3).map(([name, metric]) => (
            <span key={name} className={cn("text-[8px] font-mono px-1 py-0.5 rounded", metric.status === "normal" && "bg-emerald-500/10 text-emerald-400", metric.status === "warning" && "bg-amber-500/10 text-amber-400", metric.status === "critical" && "bg-red-500/10 text-red-400")}>
              {name.slice(0, 6)}:{metric.value.toFixed(1)}{metric.unit}
            </span>
          ))}
        </div>
      )}
      {node.folderPath != null && <p className="text-[9px] text-muted-foreground/50 mt-1 font-mono truncate">{node.folderPath}</p>}
    </motion.div>
  );
}

/* -- Edge Line -- */
function EdgeLine({ edge, nodes }: { edge: CanvasEdge; nodes: CanvasNode[] }) {
  const source = nodes.find((n) => n.id === edge.source);
  const target = nodes.find((n) => n.id === edge.target);
  if (source == null || target == null) return null;
  const sx = source.x + source.width / 2; const sy = source.y + source.height / 2;
  const tx = target.x + target.width / 2; const ty = target.y + target.height / 2;
  const colors: Record<string, string> = { dependency: "rgba(34, 211, 238, 0.25)", flow: "rgba(103, 232, 249, 0.2)", data: "rgba(16, 185, 129, 0.2)", control: "rgba(245, 158, 11, 0.2)", group: "rgba(255, 255, 255, 0.06)" };
  return (
    <svg className="absolute inset-0 pointer-events-none" style={{ width: "100%", height: "100%" }}>
      <line x1={sx} y1={sy} x2={tx} y2={ty} stroke={colors[edge.type] ?? colors.dependency} strokeWidth={1.5} strokeDasharray={edge.type === "flow" ? "4 4" : undefined} />
    </svg>
  );
}

/* -- Tape Particle -- */
function TapeParticle({ event, nodes, index }: { event: TapeEventEntry; nodes: CanvasNode[]; index: number }) {
  const source = event.source_node_id ? nodes.find((n) => n.id === event.source_node_id) : null;
  const target = event.target_node_id ? nodes.find((n) => n.id === event.target_node_id) : null;
  if (source == null || target == null) return null;
  return (
    <motion.circle r={3} fill="rgba(245, 158, 11, 0.6)" initial={{ cx: source.x + source.width / 2, cy: source.y + source.height / 2 }} animate={{ cx: target.x + target.width / 2, cy: target.y + target.height / 2 }} transition={{ duration: 1.5 + index * 0.3, repeat: Infinity, repeatType: "loop", ease: "linear", delay: index * 0.2 }} />
  );
}

/* -- Context Menu -- */
function ContextMenuComponent({ menu, onClose }: { menu: { visible: boolean; x: number; y: number; items: { label: string; action: () => void; icon?: React.ElementType }[] }; onClose: () => void }) {
  if (!menu.visible) return null;
  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} style={{ left: menu.x, top: menu.y }} className="fixed z-50 min-w-[180px] rounded-lg border border-white/[0.08] bg-inkos-navy-900/95 backdrop-blur-md shadow-xl py-1">
      {menu.items.map((item, i) => { const Icon = item.icon; return <button key={i} onClick={() => { item.action(); onClose(); }} className="w-full flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-white/[0.05] transition-colors">{Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}{item.label}</button>; })}
    </motion.div>
  );
}

/* -- Node Palette -- */
function NodePalette({ nodeTypes, onDragStart }: { nodeTypes: NodeTypeDef[]; onDragStart: (e: React.DragEvent, nt: NodeTypeDef) => void }) {
  return (
    <div className="w-56 border-r border-white/[0.04] bg-inkos-navy-900/50 flex flex-col overflow-hidden shrink-0">
      <div className="shrink-0 border-b border-white/[0.04] px-4 py-3">
        <div className="flex items-center gap-2"><Plus className="h-4 w-4 text-inkos-cyan" /><span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Node Palette</span></div>
        <p className="text-[10px] text-muted-foreground/50 mt-1">Drag nodes to canvas</p>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1.5">
        {nodeTypes.map((nt) => (<NodePaletteItem key={nt.id} nodeType={nt} onDragStart={onDragStart} />))}
      </div>
      <div className="shrink-0 border-t border-white/[0.04] px-4 py-2"><p className="text-[9px] text-muted-foreground/40 text-center">Right-click canvas to add nodes</p></div>
    </div>
  );
}

function NodePaletteItem({ nodeType, onDragStart }: { nodeType: NodeTypeDef; onDragStart: (e: React.DragEvent, nt: NodeTypeDef) => void }) {
  const Icon = nodeType.icon;
  return (
    <motion.div draggable whileHover={{ scale: 1.02, x: 2 }} onDragStart={(e) => onDragStart(e as unknown as React.DragEvent, nodeType)}
      className="group flex items-center gap-2.5 rounded-lg border border-white/[0.04] bg-white/[0.01] p-2 cursor-grab active:cursor-grabbing hover:bg-white/[0.03] hover:border-inkos-cyan/20 transition-all" style={{ borderLeftColor: nodeType.color, borderLeftWidth: 3 }}
    >
      <div className="h-7 w-7 rounded-md flex items-center justify-center shrink-0" style={{ backgroundColor: `${nodeType.color}15` }}><Icon className="h-3.5 w-3.5" style={{ color: nodeType.color }} /></div>
      <div className="flex-1 min-w-0"><p className="text-[11px] font-medium text-foreground truncate">{nodeType.label}</p><p className="text-[9px] text-muted-foreground/60 truncate">{nodeType.description}</p></div>
    </motion.div>
  );
}

/* -- Copilot Panel -- */
function CopilotPanel({ suggestions, domainId }: { suggestions: CopilotSuggestion[]; domainId: string }) {
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const handleApply = useCallback(async (s: CopilotSuggestion) => {
    if (!s.auto_applicable) return;
    setApplyingId(s.suggestion_id);
    try { await fetch(`/api/canvas/${encodeURIComponent(domainId)}/copilot/${s.suggestion_id}/apply`, { method: "POST" }); } catch { /* silent */ }
    setApplyingId(null);
  }, [domainId]);

  const typeIcons: Record<string, React.ElementType> = { ux_issue: AlertTriangle, layout_optimization: LayoutGrid, ab_variant: Eye, auto_optimization: Sparkles, missing_connection: ArrowRight, redundant_node: Bug, best_practice: Lightbulb };
  const typeColors: Record<string, string> = { ux_issue: "text-amber-400", layout_optimization: "text-inkos-cyan", ab_variant: "text-pink-400", auto_optimization: "text-emerald-400", missing_connection: "text-blue-400", redundant_node: "text-red-400", best_practice: "text-inkos-purple" };

  return (
    <div className="p-3 space-y-2">
      <div className="flex items-center justify-between mb-2"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5 text-inkos-purple" />Prime Co-Pilot</h3><span className="text-[10px] text-muted-foreground/50">{suggestions.length} suggestions</span></div>
      {suggestions.length === 0 ? <div className="text-xs text-muted-foreground text-center py-8">No suggestions -- canvas looks great!</div> : suggestions.map((s) => {
        const Icon = typeIcons[s.suggestion_type] ?? Lightbulb;
        const color = typeColors[s.suggestion_type] ?? "text-muted-foreground";
        return (
          <motion.div key={s.suggestion_id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="rounded-lg border border-white/[0.04] bg-white/[0.01] p-3 hover:bg-white/[0.02] transition-all">
            <div className="flex items-start gap-2">
              <Icon className={cn("h-4 w-4 shrink-0 mt-0.5", color)} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-foreground">{s.title}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{s.description}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={cn("text-[9px] font-mono px-1.5 py-0.5 rounded", s.impact === "high" ? "bg-red-500/10 text-red-400" : s.impact === "medium" ? "bg-amber-500/10 text-amber-400" : "bg-white/[0.03] text-muted-foreground")}>{s.impact} impact</span>
                  <span className="text-[9px] font-mono text-muted-foreground/50">{Math.round(s.confidence * 100)}%</span>
                  {s.auto_applicable && <button onClick={() => handleApply(s)} disabled={applyingId === s.suggestion_id} className="ml-auto text-[9px] font-medium px-2 py-0.5 rounded bg-inkos-cyan/10 text-inkos-cyan border border-inkos-cyan/15 hover:bg-inkos-cyan/20 transition-all disabled:opacity-30">{applyingId === s.suggestion_id ? "Applying..." : "Apply"}</button>}
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

/* -- Version Panel -- */
function VersionPanel({ versions, domainId }: { versions: CanvasVersion[]; domainId: string }) {
  const handleRewind = useCallback(async (version: number) => {
    try { await fetch(`/api/canvas/${encodeURIComponent(domainId)}/versions/${version}/rewind`, { method: "POST" }); } catch { /* silent */ }
  }, [domainId]);

  return (
    <div className="p-3 space-y-1">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mb-3"><History className="h-3.5 w-3.5 text-inkos-cyan" />AetherGit Versions</h3>
      {versions.length === 0 ? <div className="text-xs text-muted-foreground text-center py-8">No versions saved yet</div> : versions.map((v) => (
        <div key={v.version} className="flex items-center gap-3 rounded-lg border border-white/[0.04] bg-white/[0.01] px-3 py-2 hover:bg-white/[0.02] transition-all group">
          <div className="h-6 w-6 rounded-full bg-inkos-cyan/10 border border-inkos-cyan/15 flex items-center justify-center text-[9px] font-mono text-inkos-cyan">{v.version}</div>
          <div className="flex-1 min-w-0"><p className="text-xs text-foreground truncate">{v.commit_message || `Version ${v.version}`}</p><p className="text-[9px] text-muted-foreground/50">{v.author} &middot; {new Date(v.created_at).toLocaleString()}</p></div>
          <button onClick={() => handleRewind(v.version)} className="shrink-0 opacity-0 group-hover:opacity-100 text-[9px] font-medium px-2 py-0.5 rounded bg-inkos-purple/10 text-inkos-purple border border-inkos-purple/15 hover:bg-inkos-purple/20 transition-all">Rewind</button>
        </div>
      ))}
    </div>
  );
}

/* -- Node Details Panel -- */
function NodeDetailsPanel({ node, metrics }: { node: CanvasNode; metrics?: Record<string, SimulationMetric> }) {
  return (
    <div className="p-3 space-y-3">
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Node Details</span>
      <div className="space-y-2">
        <DetailRow label="Label" value={node.label} />
        <DetailRow label="Type" value={node.type} />
        {node.folderPath && <DetailRow label="Path" value={node.folderPath} mono />}
        {node.description && <div><span className="text-[10px] text-muted-foreground uppercase">Description</span><p className="text-xs text-muted-foreground leading-relaxed mt-0.5">{node.description}</p></div>}
      </div>
      {metrics && Object.keys(metrics).length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] text-muted-foreground uppercase flex items-center gap-1"><Activity className="h-3 w-3 text-emerald-400" />Simulation Metrics</p>
          {Object.entries(metrics).map(([name, m]) => (
            <div key={name} className="flex items-center justify-between rounded-md border border-white/[0.04] bg-white/[0.01] px-2 py-1.5">
              <span className="text-[10px] text-muted-foreground">{name}</span>
              <span className={cn("text-xs font-mono", m.status === "normal" && "text-emerald-400", m.status === "warning" && "text-amber-400", m.status === "critical" && "text-red-400")}>
                {m.value.toFixed(2)}{m.unit}{m.trend === "improving" && " ↑"}{m.trend === "degrading" && " ↓"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return <div><span className="text-[10px] text-muted-foreground uppercase">{label}</span><p className={cn("text-xs", mono && "font-mono text-muted-foreground")}>{value}</p></div>;
}

function EmptyPanel() {
  return <div className="flex flex-col items-center justify-center py-12 text-center"><Network className="h-8 w-8 text-muted-foreground/20 mb-3" /><p className="text-xs text-muted-foreground/50">Select a node to view details</p></div>;
}
