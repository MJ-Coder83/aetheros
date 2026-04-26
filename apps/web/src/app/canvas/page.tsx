"use client";

import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  Suspense,
  useRef,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "next/navigation";
import {
  Network,
  Layers,
  CheckCircle2,
  X,
  Cpu,
  Lightbulb,
  Users,
  History,
  Zap,
  Terminal,
  Monitor,
  Puzzle,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Folder,
  FileCode,
  GitBranch,
  Sparkles,
  AlertTriangle,
  ArrowRight,
  Activity,
  Maximize2,
  LayoutGrid,
  Send,
  Loader2,
  Shield,
  Bug,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { CanvasNode, CanvasEdge, CanvasLayout } from "@/types/canvas";
import type {
  CopilotSuggestion,
  CopilotSuggestionType,
  NLEditResult,
  SimulationMetric,
  TapeEventEntry,
  CanvasVersion,
  CanvasViewMode,
  SwarmMode,
} from "@/types/canvas-v5";

/* ═══════════════════════════════════════════════════════════════════
   Main Page Component
   ═══════════════════════════════════════════════════════════════════ */

export default function CanvasPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-1 items-center justify-center min-h-screen">
          <div className="text-sm text-muted-foreground">Loading canvas...</div>
        </div>
      }
    >
      <CanvasPageContent />
    </Suspense>
  );
}

function CanvasPageContent() {
  const searchParams = useSearchParams();
  const domainId = searchParams.get("domain_id") || "demo-domain";
  const isNewlyCreated = searchParams.get("from_creation") === "true";

  // Core state
  const [viewMode, setViewMode] = useState<CanvasViewMode>("visual");
  const [layout, setLayout] = useState<CanvasLayout>("smart");
  const [canvasNodes, setCanvasNodes] = useState<CanvasNode[]>([]);
  const [canvasEdges, setCanvasEdges] = useState<CanvasEdge[]>([]);
  const [canvasLoaded, setCanvasLoaded] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [scale, setScale] = useState(1);

  // V5 feature state
  const [showSimulationOverlay, setShowSimulationOverlay] = useState(false);
  const [showTapeOverlay, setShowTapeOverlay] = useState(false);
  const [showCopilot, setShowCopilot] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showNLEditor, setShowNLEditor] = useState(false);
  const [nlInput, setNlInput] = useState("");
  const [nlProcessing, setNlProcessing] = useState(false);
  const [nlLastResult, setNlLastResult] = useState<NLEditResult | null>(null);

  // Copilot state
  const [copilotSuggestions, setCopilotSuggestions] = useState<
    CopilotSuggestion[]
  >([]);

  // Simulation overlay data
  const [simulationMetrics, setSimulationMetrics] = useState<
    Record<string, Record<string, SimulationMetric>>
  >({});

  // Tape overlay data
  const [tapeEvents, setTapeEvents] = useState<TapeEventEntry[]>([]);

  // Version history
  const [versions, setVersions] = useState<CanvasVersion[]>([]);

  // Error state
  const [error, setError] = useState<string | null>(null);

  // Success banner
  const [showBanner, setShowBanner] = useState(isNewlyCreated);

  useEffect(() => {
    if (isNewlyCreated) {
      const timer = setTimeout(() => setShowBanner(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [isNewlyCreated]);

  // Load canvas data with proper error handling
  useEffect(() => {
    async function fetchCanvas() {
      setError(null);
      try {
        const res = await fetch(`/api/canvas/${encodeURIComponent(domainId)}`);
        if (!res.ok) {
          const errorData = await res.json().catch(() => null);
          throw new Error(
            errorData?.detail || `Failed to load canvas: ${res.status}`,
          );
        }
        const data = await res.json();
        setCanvasNodes(data.nodes ?? []);
        setCanvasEdges(data.edges ?? []);
        setCanvasLoaded(true);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load canvas";
        setError(message);
        setCanvasNodes([]);
        setCanvasEdges([]);
        setCanvasLoaded(true);
        // Log to console for debugging
        console.error("Canvas load error:", err);
      }
    }
    fetchCanvas();
  }, [domainId]);

  // Fetch copilot suggestions on demand
  const fetchCopilotSuggestions = useCallback(async () => {
    try {
      const res = await fetch(`/api/canvas/${domainId}/copilot`);
      if (res.ok) {
        const data = await res.json();
        setCopilotSuggestions(data.suggestions ?? []);
        return;
      }
    } catch (err) {
      console.error("Fetch error:", err);
    }
    setCopilotSuggestions([]);
  }, [domainId]);

  // Fetch simulation overlay
  const fetchSimulationOverlay = useCallback(async () => {
    try {
      const res = await fetch(`/api/canvas/${domainId}/simulation-overlay`);
      if (res.ok) {
        const data = await res.json();
        setSimulationMetrics(data.overlay ?? {});
        return;
      }
    } catch (err) {
      console.error("Fetch error:", err);
    }
    setSimulationMetrics({});
  }, [domainId, canvasNodes]);

  // Fetch tape overlay
  const fetchTapeOverlay = useCallback(async () => {
    try {
      const res = await fetch(`/api/canvas/${domainId}/tape-overlay?limit=20`);
      if (res.ok) {
        const data = await res.json();
        setTapeEvents(data.events ?? []);
        return;
      }
    } catch (err) {
      console.error("Fetch error:", err);
    }
    setTapeEvents([]);
  }, [domainId]);

  // Fetch version history
  const fetchVersions = useCallback(async () => {
    try {
      const res = await fetch(`/api/canvas/${domainId}/versions`);
      if (res.ok) {
        const data = await res.json();
        setVersions(data.versions ?? []);
        return;
      }
    } catch (err) {
      console.error("Fetch error:", err);
    }
    setVersions([]);
  }, [domainId]);

  // NL edit handler
  const handleNLSubmit = useCallback(async () => {
    if (!nlInput.trim()) return;
    setNlProcessing(true);
    try {
      const res = await fetch(`/api/canvas/${domainId}/nl-edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: nlInput }),
      });
      if (res.ok) {
        const data = await res.json();
        setNlLastResult(data);
        setNlInput("");
        // Refresh canvas
        const canvasRes = await fetch(`/api/canvas/${domainId}`);
        if (canvasRes.ok) {
          const canvasData = await canvasRes.json();
          setCanvasNodes(canvasData.nodes ?? canvasNodes);
          setCanvasEdges(canvasData.edges ?? canvasEdges);
        }
      }
    } catch (err) {
      setNlLastResult({
        edit_id: "error",
        instruction: nlInput,
        edit_type: "compound",
        confidence: 0,
        applied: false,
        changes: [],
        error: "Failed to apply edit",
      });
    }
    setNlProcessing(false);
  }, [nlInput, domainId, canvasNodes, canvasEdges]);

  // Swarm handler
  const handleSwarm = useCallback(
    async (mode: SwarmMode) => {
      const task =
        mode === "quick" ? "Optimize layout" : "Reorganize domain structure";
      try {
        await fetch(`/api/canvas/${domainId}/swarm`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task, mode }),
        });
      } catch (err) {
        // Silent
      }
    },
    [domainId],
  );

  // Overlays auto-fetch
  useEffect(() => {
    if (showSimulationOverlay) fetchSimulationOverlay();
  }, [showSimulationOverlay, fetchSimulationOverlay]);

  useEffect(() => {
    if (showTapeOverlay) fetchTapeOverlay();
  }, [showTapeOverlay, fetchTapeOverlay]);

  useEffect(() => {
    if (showCopilot) fetchCopilotSuggestions();
  }, [showCopilot, fetchCopilotSuggestions]);

  useEffect(() => {
    if (showVersionHistory) fetchVersions();
  }, [showVersionHistory, fetchVersions]);

  const selectedNode = useMemo(
    () => canvasNodes.find((n) => n.id === selectedNodeId),
    [canvasNodes, selectedNodeId],
  );

  return (
    <div className="flex flex-col flex-1 min-h-0 page-transition">
      {/* ═══ Header ═══ */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="shrink-0 border-b border-white/[0.04] bg-background/80 backdrop-blur-sm"
      >
        <div className="flex items-center justify-between px-4 sm:px-6 py-3">
          {/* Left: Branding */}
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center">
              <Network className="h-5 w-5 text-inkos-cyan" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
                <span className="text-inkos-cyan text-glow-cyan">Domain</span>
                <span className="text-foreground">Canvas</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-inkos-purple/30 text-inkos-purple bg-inkos-purple/5">
                  v5
                </span>
              </h1>
              <p className="text-xs text-muted-foreground">
                {canvasLoaded ? `Domain: ${domainId}` : "Loading..."}
              </p>
            </div>
          </div>

          {/* Center: Feature toggles */}
          <div className="hidden md:flex items-center gap-1">
            <FeatureToggle
              icon={Activity}
              label="Sim"
              active={showSimulationOverlay}
              onClick={() => setShowSimulationOverlay(!showSimulationOverlay)}
              color="text-emerald-400"
            />
            <FeatureToggle
              icon={Zap}
              label="Tape"
              active={showTapeOverlay}
              onClick={() => setShowTapeOverlay(!showTapeOverlay)}
              color="text-amber-400"
            />
            <FeatureToggle
              icon={Sparkles}
              label="Co-Pilot"
              active={showCopilot}
              onClick={() => {
                setShowCopilot(!showCopilot);
              }}
              color="text-inkos-purple"
            />
            <FeatureToggle
              icon={History}
              label="Versions"
              active={showVersionHistory}
              onClick={() => setShowVersionHistory(!showVersionHistory)}
              color="text-inkos-cyan"
            />
            <FeatureToggle
              icon={Sparkles}
              label="NL Edit"
              active={showNLEditor}
              onClick={() => setShowNLEditor(!showNLEditor)}
              color="text-pink-400"
            />
            <div className="h-4 w-px bg-white/[0.06] mx-1" />
            <SwarmButton mode="quick" onClick={() => handleSwarm("quick")} />
            <SwarmButton
              mode="governed"
              onClick={() => handleSwarm("governed")}
            />
          </div>

          {/* Right: Layout + View mode */}
          <div className="flex items-center gap-3">
            <LayoutSelector layout={layout} onChange={setLayout} />
            <ViewModeToggle mode={viewMode} onChange={setViewMode} />
          </div>
        </div>
      </motion.div>

      {/* ═══ Success Banner ═══ */}
      <AnimatePresence>
        {showBanner && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="shrink-0 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 sm:px-6 py-2 bg-emerald-500/8 border-b border-emerald-500/15">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span className="text-xs font-medium text-emerald-300">
                  Canvas v5 ready -- visual development environment with
                  Co-Pilot, Swarms, and AetherGit versioning
                </span>
              </div>
              <button
                onClick={() => setShowBanner(false)}
                className="rounded-md p-1 text-emerald-400/60 hover:text-emerald-300 transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ Main Workspace ═══ */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {viewMode === "visual" ? (
          <>
            {/* Canvas area */}
            <div className="relative flex-1 overflow-hidden bg-background">
              {/* Grid background */}
              <div
                className="absolute inset-0 opacity-[0.03]"
                style={{
                  backgroundImage: `linear-gradient(rgba(34, 211, 238, 0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(34, 211, 238, 0.5) 1px, transparent 1px)`,
                  backgroundSize: `${24 * scale}px ${24 * scale}px`,
                }}
              />

              {/* Scaled content */}
              <div
                className="absolute inset-0"
                style={{
                  transform: `scale(${scale})`,
                  transformOrigin: "top left",
                }}
              >
                {/* Edges */}
                {canvasEdges.map((edge) => (
                  <EdgeLine key={edge.id} edge={edge} nodes={canvasNodes} />
                ))}

                {/* Tape overlay particles */}
                {showTapeOverlay &&
                  tapeEvents
                    .slice(0, 10)
                    .map((event, i) => (
                      <TapeParticle
                        key={event.event_id}
                        event={event}
                        nodes={canvasNodes}
                        index={i}
                      />
                    ))}

                {/* Nodes */}
                {canvasNodes.map((node) => (
                  <NodeCardV5
                    key={node.id}
                    node={node}
                    isSelected={selectedNodeId === node.id}
                    onSelect={setSelectedNodeId}
                    simulationMetrics={
                      showSimulationOverlay
                        ? simulationMetrics[node.id]
                        : undefined
                    }
                  />
                ))}
              </div>

              {/* Zoom controls */}
              <div className="absolute bottom-4 right-4 flex items-center gap-1 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-900/90 backdrop-blur-sm p-1">
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
                <div className="w-px h-4 bg-white/[0.06] mx-1" />
                <button
                  onClick={() => {
                    setScale(1);
                    setSelectedNodeId(null);
                  }}
                  className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"
                  title="Reset view"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* NL Edit bar (bottom) */}
              {showNLEditor && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute bottom-16 left-4 right-4 max-w-2xl mx-auto"
                >
                  <div className="glass rounded-xl border border-inkos-purple/20 p-3 flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-inkos-purple shrink-0" />
                    <input
                      type="text"
                      value={nlInput}
                      onChange={(e) => setNlInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleNLSubmit()}
                      placeholder='Natural language edit — "Move the domain node to the center"'
                      className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 outline-none"
                      disabled={nlProcessing}
                    />
                    <button
                      onClick={handleNLSubmit}
                      disabled={nlProcessing || !nlInput.trim()}
                      className="shrink-0 h-8 px-3 rounded-lg bg-inkos-purple/20 border border-inkos-purple/30 text-inkos-purple text-xs font-medium hover:bg-inkos-purple/30 transition-all disabled:opacity-30"
                    >
                      {nlProcessing ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Send className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                  {nlLastResult && (
                    <div
                      className={cn(
                        "mt-1 text-xs px-3 py-1.5 rounded-lg text-center",
                        nlLastResult.applied
                          ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/15"
                          : "bg-red-500/10 text-red-300 border border-red-500/15",
                      )}
                    >
                      {nlLastResult.applied
                        ? `Applied: ${nlLastResult.edit_type} (${Math.round(nlLastResult.confidence * 100)}% confidence)`
                        : `Failed: ${nlLastResult.error || "Could not parse instruction"}`}
                    </div>
                  )}
                </motion.div>
              )}
            </div>

            {/* Right panel */}
            <div className="w-80 border-l border-white/[0.04] bg-inkos-navy-900/50 flex flex-col overflow-hidden">
              {/* Panel tabs */}
              <div className="shrink-0 flex border-b border-white/[0.04]">
                <PanelTab
                  icon={Users}
                  label="Details"
                  active={!showCopilot && !showVersionHistory}
                  onClick={() => {
                    setShowCopilot(false);
                    setShowVersionHistory(false);
                  }}
                />
                <PanelTab
                  icon={Sparkles}
                  label="Co-Pilot"
                  active={showCopilot}
                  onClick={() => {
                    setShowCopilot(true);
                    setShowVersionHistory(false);
                  }}
                />
                <PanelTab
                  icon={History}
                  label="Versions"
                  active={showVersionHistory}
                  onClick={() => {
                    setShowVersionHistory(true);
                    setShowCopilot(false);
                  }}
                />
              </div>

              <div className="flex-1 overflow-auto">
                {showCopilot ? (
                  <CopilotPanel
                    suggestions={copilotSuggestions}
                    domainId={domainId}
                  />
                ) : showVersionHistory ? (
                  <VersionPanel versions={versions} domainId={domainId} />
                ) : selectedNode ? (
                  <NodeDetailsPanel
                    node={selectedNode}
                    metrics={simulationMetrics[selectedNode.id]}
                  />
                ) : (
                  <EmptyPanel />
                )}
              </div>
            </div>
          </>
        ) : (
          <FolderModeView />
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   Sub-Components
   ═══════════════════════════════════════════════════════════════════ */

function FeatureToggle({
  icon: Icon,
  label,
  active,
  onClick,
  color,
}: {
  icon: React.ElementType;
  label: string;
  active: boolean;
  onClick: () => void;
  color: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-all",
        active
          ? `${color} bg-white/[0.05] border border-white/[0.08]`
          : "text-muted-foreground hover:text-foreground border border-transparent",
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      <span className="hidden lg:inline">{label}</span>
    </button>
  );
}

function SwarmButton({
  mode,
  onClick,
}: {
  mode: SwarmMode;
  onClick: () => void;
}) {
  const isQuick = mode === "quick";
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all",
        isQuick
          ? "text-inkos-cyan border border-inkos-cyan/15 hover:bg-inkos-cyan/5"
          : "text-amber-400 border border-amber-400/15 hover:bg-amber-400/5",
      )}
    >
      {isQuick ? (
        <Zap className="h-3.5 w-3.5" />
      ) : (
        <Shield className="h-3.5 w-3.5" />
      )}
      <span className="hidden lg:inline">{isQuick ? "Quick" : "Governed"}</span>
    </button>
  );
}

function ViewModeToggle({
  mode,
  onChange,
}: {
  mode: CanvasViewMode;
  onChange: (m: CanvasViewMode) => void;
}) {
  return (
    <div className="inline-flex items-center rounded-lg border border-inkos-cyan/10 bg-inkos-navy-800/40 p-[3px]">
      <button
        onClick={() => onChange("visual")}
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
        onClick={() => onChange("folder")}
        className={cn(
          "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
          mode === "folder"
            ? "bg-inkos-cyan/15 text-inkos-cyan shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        <Layers className="h-3.5 w-3.5" />
        Folder
      </button>
    </div>
  );
}

function LayoutSelector({
  layout,
  onChange,
}: {
  layout: CanvasLayout;
  onChange: (l: CanvasLayout) => void;
}) {
  const options: {
    value: CanvasLayout;
    label: string;
    icon: React.ElementType;
  }[] = [
    { value: "smart", label: "Smart Auto", icon: Cpu },
    { value: "layered", label: "Layered", icon: LayoutGrid },
    { value: "hub-and-spoke", label: "Hub & Spoke", icon: Network },
    { value: "clustered", label: "Clustered", icon: Layers },
    { value: "linear", label: "Linear", icon: Maximize2 },
  ];

  return (
    <div className="relative group">
      <button className="flex items-center gap-1.5 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-800/40 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-all">
        {(() => {
          const active = options.find((o) => o.value === layout) ?? options[0];
          return (
            <>
              <active.icon className="h-3.5 w-3.5" />
              {active.label}
            </>
          );
        })()}
      </button>
      <div className="absolute right-0 top-full mt-1 z-50 w-40 rounded-lg border border-inkos-cyan/10 bg-inkos-navy-900 shadow-xl overflow-hidden hidden group-hover:block">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
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
      </div>
    </div>
  );
}

function PanelTab({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-all border-b-2",
        active
          ? "text-inkos-cyan border-inkos-cyan"
          : "text-muted-foreground border-transparent hover:text-foreground",
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

/* -- Node Card (v5 with simulation overlay) -- */

const TYPE_ICONS: Record<string, React.ReactNode> = {
  agent: <Cpu className="h-4 w-4" />,
  skill: <FileCode className="h-4 w-4" />,
  workflow: <GitBranch className="h-4 w-4" />,
  domain: <Network className="h-4 w-4" />,
  browser: <Monitor className="h-4 w-4" />,
  terminal: <Terminal className="h-4 w-4" />,
  plugin: <Puzzle className="h-4 w-4" />,
  custom: <Puzzle className="h-4 w-4" />,
};

const TYPE_COLORS: Record<string, string> = {
  agent: "border-cyan-400/30 text-cyan-400",
  skill: "border-emerald-400/30 text-emerald-400",
  workflow: "border-amber-400/30 text-amber-400",
  domain: "border-indigo-400/30 text-indigo-400",
  browser: "border-blue-400/30 text-blue-400",
  terminal: "border-green-400/30 text-green-400",
  plugin: "border-purple-400/30 text-purple-400",
  custom: "border-slate-400/30 text-slate-400",
};

function NodeCardV5({
  node,
  isSelected,
  onSelect,
  simulationMetrics,
}: {
  node: CanvasNode;
  isSelected: boolean;
  onSelect: (id: string) => void;
  simulationMetrics?: Record<string, SimulationMetric>;
}) {
  const typeKey = node.type || "custom";
  const iconEl = TYPE_ICONS[typeKey] ?? TYPE_ICONS.custom;
  const colorClass = TYPE_COLORS[typeKey] ?? TYPE_COLORS.custom;

  // Get worst simulation status
  const worstStatus = simulationMetrics
    ? Object.values(simulationMetrics).reduce<string>((worst, m) => {
        if (m.status === "critical") return "critical";
        if (m.status === "warning" && worst !== "critical") return "warning";
        return worst;
      }, "normal")
    : "normal";

  const statusBorderClass =
    worstStatus === "critical"
      ? "border-red-500/50 shadow-red-500/10"
      : worstStatus === "warning"
        ? "border-amber-500/40 shadow-amber-500/5"
        : "";

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
          : "border-white/[0.06] bg-card/80 hover:border-inkos-cyan/20",
        statusBorderClass && `shadow-md ${statusBorderClass}`,
      )}
      style={{
        left: node.x,
        top: node.y,
        width: node.width,
        height: node.height,
      }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-inkos-cyan">{iconEl}</span>
        <span className="text-xs font-semibold truncate">{node.label}</span>
        <span
          className={cn(
            "ml-auto text-[9px] font-mono uppercase px-1 py-0.5 rounded border",
            colorClass,
          )}
        >
          {typeKey}
        </span>
      </div>

      {node.description != null && (
        <p className="text-[10px] text-muted-foreground line-clamp-2 leading-relaxed">
          {node.description}
        </p>
      )}

      {/* Simulation overlay badges */}
      {simulationMetrics && (
        <div className="flex items-center gap-1 mt-1.5">
          {Object.entries(simulationMetrics)
            .slice(0, 3)
            .map(([name, metric]) => (
              <span
                key={name}
                className={cn(
                  "text-[8px] font-mono px-1 py-0.5 rounded",
                  metric.status === "normal" &&
                    "bg-emerald-500/10 text-emerald-400",
                  metric.status === "warning" &&
                    "bg-amber-500/10 text-amber-400",
                  metric.status === "critical" && "bg-red-500/10 text-red-400",
                )}
              >
                {name.slice(0, 6)}:{metric.value.toFixed(1)}
                {metric.unit}
              </span>
            ))}
        </div>
      )}

      {node.folderPath != null && (
        <p className="text-[9px] text-muted-foreground/50 mt-1 font-mono truncate">
          {node.folderPath}
        </p>
      )}
    </motion.div>
  );
}

/* -- Edge Line -- */

function EdgeLine({ edge, nodes }: { edge: CanvasEdge; nodes: CanvasNode[] }) {
  const source = nodes.find((n) => n.id === edge.source);
  const target = nodes.find((n) => n.id === edge.target);
  if (source == null || target == null) return null;

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
    </svg>
  );
}

/* -- Tape Overlay Particle -- */

function TapeParticle({
  event,
  nodes,
  index,
}: {
  event: TapeEventEntry;
  nodes: CanvasNode[];
  index: number;
}) {
  const source = event.source_node_id
    ? nodes.find((n) => n.id === event.source_node_id)
    : null;
  const target = event.target_node_id
    ? nodes.find((n) => n.id === event.target_node_id)
    : null;
  if (source == null || target == null) return null;

  const sx = source.x + source.width / 2;
  const sy = source.y + source.height / 2;
  const tx = target.x + target.width / 2;
  const ty = target.y + target.height / 2;

  return (
    <motion.circle
      r={3}
      fill="rgba(245, 158, 11, 0.6)"
      initial={{ cx: sx, cy: sy }}
      animate={{ cx: tx, cy: ty }}
      transition={{
        duration: 1.5 + index * 0.3,
        repeat: Infinity,
        repeatType: "loop",
        ease: "linear",
        delay: index * 0.2,
      }}
    />
  );
}

/* -- Copilot Panel -- */

function CopilotPanel({
  suggestions,
  domainId,
}: {
  suggestions: CopilotSuggestion[];
  domainId: string;
}) {
  const [applyingId, setApplyingId] = useState<string | null>(null);

  const handleApply = useCallback(
    async (suggestion: CopilotSuggestion) => {
      if (!suggestion.auto_applicable) return;
      setApplyingId(suggestion.suggestion_id);
      try {
        await fetch(
          `/api/canvas/${domainId}/copilot/${suggestion.suggestion_id}/apply`,
          {
            method: "POST",
          },
        );
      } catch (err) {
        // Silent
      }
      setApplyingId(null);
    },
    [domainId],
  );

  const typeIcons: Record<CopilotSuggestionType, React.ElementType> = {
    ux_issue: AlertTriangle,
    layout_optimization: LayoutGrid,
    ab_variant: Maximize2,
    auto_optimization: Sparkles,
    missing_connection: ArrowRight,
    redundant_node: Bug,
    best_practice: Lightbulb,
  };

  const typeColors: Record<CopilotSuggestionType, string> = {
    ux_issue: "text-amber-400",
    layout_optimization: "text-inkos-cyan",
    ab_variant: "text-pink-400",
    auto_optimization: "text-emerald-400",
    missing_connection: "text-blue-400",
    redundant_node: "text-red-400",
    best_practice: "text-inkos-purple",
  };

  return (
    <div className="p-3 space-y-2">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-inkos-purple" />
          Prime Co-Pilot
        </h3>
        <span className="text-[10px] text-muted-foreground/50">
          {suggestions.length} suggestions
        </span>
      </div>

      {suggestions.length === 0 ? (
        <div className="text-xs text-muted-foreground text-center py-8">
          No suggestions -- canvas looks great!
        </div>
      ) : (
        suggestions.map((s) => {
          const Icon = typeIcons[s.suggestion_type] ?? Lightbulb;
          const color =
            typeColors[s.suggestion_type] ?? "text-muted-foreground";
          return (
            <motion.div
              key={s.suggestion_id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-lg border border-white/[0.04] bg-white/[0.01] p-3 hover:bg-white/[0.02] transition-all"
            >
              <div className="flex items-start gap-2">
                <Icon className={cn("h-4 w-4 shrink-0 mt-0.5", color)} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-foreground">
                    {s.title}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">
                    {s.description}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span
                      className={cn(
                        "text-[9px] font-mono px-1.5 py-0.5 rounded",
                        s.impact === "high"
                          ? "bg-red-500/10 text-red-400"
                          : s.impact === "medium"
                            ? "bg-amber-500/10 text-amber-400"
                            : "bg-white/[0.03] text-muted-foreground",
                      )}
                    >
                      {s.impact} impact
                    </span>
                    <span className="text-[9px] font-mono text-muted-foreground/50">
                      {Math.round(s.confidence * 100)}%
                    </span>
                    {s.auto_applicable && (
                      <button
                        onClick={() => handleApply(s)}
                        disabled={applyingId === s.suggestion_id}
                        className="ml-auto text-[9px] font-medium px-2 py-0.5 rounded bg-inkos-cyan/10 text-inkos-cyan border border-inkos-cyan/15 hover:bg-inkos-cyan/20 transition-all disabled:opacity-30"
                      >
                        {applyingId === s.suggestion_id
                          ? "Applying..."
                          : "Apply"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })
      )}
    </div>
  );
}

/* -- Version History Panel -- */

function VersionPanel({
  versions,
  domainId,
}: {
  versions: CanvasVersion[];
  domainId: string;
}) {
  const handleRewind = useCallback(
    async (version: number) => {
      try {
        await fetch(`/api/canvas/${domainId}/versions/${version}/rewind`, {
          method: "POST",
        });
      } catch (err) {
        // Silent
      }
    },
    [domainId],
  );

  return (
    <div className="p-3 space-y-1">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mb-3">
        <History className="h-3.5 w-3.5 text-inkos-cyan" />
        AetherGit Versions
      </h3>

      {versions.length === 0 ? (
        <div className="text-xs text-muted-foreground text-center py-8">
          No versions saved yet
        </div>
      ) : (
        versions.map((v) => (
          <div
            key={v.version}
            className="flex items-center gap-3 rounded-lg border border-white/[0.04] bg-white/[0.01] px-3 py-2 hover:bg-white/[0.02] transition-all group"
          >
            <div className="h-6 w-6 rounded-full bg-inkos-cyan/10 border border-inkos-cyan/15 flex items-center justify-center text-[9px] font-mono text-inkos-cyan">
              {v.version}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-foreground truncate">
                {v.commit_message || `Version ${v.version}`}
              </p>
              <p className="text-[9px] text-muted-foreground/50">
                {v.author} &middot; {new Date(v.created_at).toLocaleString()}
              </p>
            </div>
            <button
              onClick={() => handleRewind(v.version)}
              className="shrink-0 opacity-0 group-hover:opacity-100 text-[9px] font-medium px-2 py-0.5 rounded bg-inkos-purple/10 text-inkos-purple border border-inkos-purple/15 hover:bg-inkos-purple/20 transition-all"
            >
              Rewind
            </button>
          </div>
        ))
      )}
    </div>
  );
}

/* -- Node Details Panel -- */

function NodeDetailsPanel({
  node,
  metrics,
}: {
  node: CanvasNode;
  metrics?: Record<string, SimulationMetric>;
}) {
  return (
    <div className="p-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Node Details
        </span>
      </div>

      <div className="space-y-2">
        <DetailRow label="Label" value={node.label} />
        <DetailRow label="Type" value={node.type} />
        {node.folderPath && (
          <DetailRow label="Path" value={node.folderPath} mono />
        )}
        {node.description && (
          <div>
            <span className="text-[10px] text-muted-foreground uppercase">
              Description
            </span>
            <p className="text-xs text-muted-foreground leading-relaxed mt-0.5">
              {node.description}
            </p>
          </div>
        )}
      </div>

      {/* Simulation Metrics */}
      {metrics && Object.keys(metrics).length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] text-muted-foreground uppercase flex items-center gap-1">
            <Activity className="h-3 w-3 text-emerald-400" />
            Simulation Metrics
          </p>
          {Object.entries(metrics).map(([name, m]) => (
            <div
              key={name}
              className="flex items-center justify-between rounded-md border border-white/[0.04] bg-white/[0.01] px-2 py-1.5"
            >
              <span className="text-[10px] text-muted-foreground">{name}</span>
              <span
                className={cn(
                  "text-xs font-mono",
                  m.status === "normal" && "text-emerald-400",
                  m.status === "warning" && "text-amber-400",
                  m.status === "critical" && "text-red-400",
                )}
              >
                {m.value.toFixed(2)}
                {m.unit}
                {m.trend === "improving" && " ↑"}
                {m.trend === "degrading" && " ↓"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <span className="text-[10px] text-muted-foreground uppercase">
        {label}
      </span>
      <p className={cn("text-xs", mono && "font-mono text-muted-foreground")}>
        {value}
      </p>
    </div>
  );
}

/* -- Empty Panel -- */

function EmptyPanel() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Network className="h-8 w-8 text-muted-foreground/20 mb-3" />
      <p className="text-xs text-muted-foreground/50">
        Select a node to view details
      </p>
    </div>
  );
}

/* -- Folder Mode View -- */

function FolderModeView() {
  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="px-4 py-2 border-b border-white/[0.04] flex items-center gap-2">
        <Layers className="h-3.5 w-3.5 text-inkos-cyan" />
        <span className="text-xs font-medium text-muted-foreground">
          Folder Tree View
        </span>
        <span className="text-[10px] text-muted-foreground/50 ml-2">
          Synchronized with visual canvas
        </span>
      </div>
      <div className="flex-1 min-h-0 p-4 overflow-auto">
        <div className="text-xs text-muted-foreground text-center py-8">
          Folder tree synced from FolderTreeService
        </div>
      </div>
    </div>
  );

  /* ═══════════════════════════════════════════════════════════════════
Licensed under MIT - InkosAI Technical Debt Cleanup
═══════════════════════════════════════════════════════════════════ */

  // Add closing brace for FolderModeView function
}

export {}; // Module boundary
