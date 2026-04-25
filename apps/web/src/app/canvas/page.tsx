"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";
import {
  Network,
  Layers,
  Plus,
} from "lucide-react";
import { ModeToggle, LayoutSelector, PrimeFeatureBar, FolderTreeView, VisualCanvasView, FolderThinkingPanel } from "@/components/canvas/canvas-views";
import type { CanvasLayout, CanvasNode, CanvasEdge } from "@/types/canvas";

export default function CanvasPage() {
  const [mode, setMode] = useState<"visual" | "folder">("visual");
  const [layout, setLayout] = useState<CanvasLayout>("smart");
  const [canvasNodes, setCanvasNodes] = useState<CanvasNode[]>([]);
  const [canvasEdges, setCanvasEdges] = useState<CanvasEdge[]>([]);
  const [canvasLoaded, setCanvasLoaded] = useState(false);
  const [loading, setLoading] = useState(false);

  const searchParams = useSearchParams();
  const canvasId = searchParams.get("canvas_id");

  // Fetch canvas data if canvas_id is provided
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
