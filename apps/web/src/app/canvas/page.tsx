"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "next/navigation";
import {
  Network,
  Layers,
  Plus,
  ArrowLeft,
  CheckCircle2,
  X,
} from "lucide-react";
import { ModeToggle, LayoutSelector, PrimeFeatureBar, FolderTreeView, VisualCanvasView, FolderThinkingPanel } from "@/components/canvas/canvas-views";
import type { CanvasLayout, CanvasNode, CanvasEdge } from "@/types/canvas";

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
  const [mode, setMode] = useState<"visual" | "folder">("visual");
  const [layout, setLayout] = useState<CanvasLayout>("smart");
  const [canvasNodes, setCanvasNodes] = useState<CanvasNode[]>([]);
  const [canvasEdges, setCanvasEdges] = useState<CanvasEdge[]>([]);
  const [canvasLoaded, setCanvasLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSuccessBanner, setShowSuccessBanner] = useState(false);

  const searchParams = useSearchParams();
  const canvasId = searchParams.get("canvas_id");
  const domainId = searchParams.get("domain_id");
  const isNewlyCreated = searchParams.get("from_creation") === "true";

  const dismissBanner = useCallback(() => setShowSuccessBanner(false), []);

  useEffect(() => {
    if (isNewlyCreated) {
      setShowSuccessBanner(true);
      const timer = setTimeout(() => setShowSuccessBanner(false), 6000);
      return () => clearTimeout(timer);
    }
  }, [isNewlyCreated]);

  useEffect(() => {
    if (!canvasId) {
      setCanvasLoaded(false);
      setCanvasNodes([]);
      setCanvasEdges([]);
      return;
    }

    async function fetchCanvas() {
      setLoading(true);
      try {
        const res = await fetch(`/api/canvas/${canvasId}`);
        if (res.ok) {
          const data = await res.json();
          setCanvasNodes(data.nodes ?? []);
          setCanvasEdges(data.edges ?? []);
          setCanvasLoaded(true);
        }
      } catch {
        // Silently fail — will show empty canvas
      } finally {
        setLoading(false);
      }
    }
    fetchCanvas();
  }, [canvasId]);

  return (
    <div className="flex flex-col flex-1 min-h-0 page-transition">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="shrink-0 border-b border-white/[0.04] bg-background/80 backdrop-blur-sm"
      >
        <div className="flex items-center justify-between px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3">
            {domainId ? (
              <a
                href={`/domains?highlight=${domainId}`}
                className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Domain
              </a>
            ) : null}
            <div className="h-9 w-9 rounded-lg bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center">
              <Network className="h-5 w-5 text-inkos-cyan" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
                <span className="text-inkos-cyan text-glow-cyan">Domain</span>
                <span className="text-foreground">Canvas</span>
              </h1>
              <p className="text-xs text-muted-foreground">
                {canvasLoaded
                  ? `Loaded canvas: ${canvasId}`
                  : "Visual development environment — dual-mode workspace"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="/domains"
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-white/[0.03] transition-all"
            >
              <Plus className="h-3.5 w-3.5" />
              Create Domain
            </a>
            <div className="h-4 w-px bg-white/[0.06]" />
            <PrimeFeatureBar />
            <div className="h-4 w-px bg-white/[0.06]" />
            <LayoutSelector layout={layout} onChange={setLayout} />
            <ModeToggle mode={mode} onChange={setMode} />
          </div>
        </div>
      </motion.div>

      {/* Success banner for newly created domain canvas */}
      <AnimatePresence>
        {showSuccessBanner && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="shrink-0 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 sm:px-6 py-2 bg-emerald-500/8 border-b border-emerald-500/15">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span className="text-xs font-medium text-emerald-300">
                  Starter canvas generated — your domain is ready for visual editing
                </span>
              </div>
              <button
                onClick={dismissBanner}
                className="rounded-md p-1 text-emerald-400/60 hover:text-emerald-300 transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main workspace */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {loading ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-sm text-muted-foreground">Loading canvas...</div>
          </div>
        ) : (
          <>
            {mode === "visual" ? (
              <>
                <VisualCanvasView
                  nodes={canvasNodes}
                  edges={canvasEdges}
                  canvasLoaded={canvasLoaded}
                />
                <FolderThinkingPanel />
              </>
            ) : (
              <>
                <div className="flex flex-col flex-1 min-h-0">
                  <div className="px-4 py-2 border-b border-white/[0.04] flex items-center gap-2">
                    <Layers className="h-3.5 w-3.5 text-inkos-cyan" />
                    <span className="text-xs font-medium text-muted-foreground">Folder Tree View</span>
                    <span className="text-[10px] text-muted-foreground/50 ml-2">
                      Synchronized with visual canvas
                    </span>
                  </div>
                  <div className="flex-1 min-h-0">
                    <FolderTreeView />
                  </div>
                </div>
                <FolderThinkingPanel />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
