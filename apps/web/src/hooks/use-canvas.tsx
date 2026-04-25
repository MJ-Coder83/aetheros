"use client";

import { createContext, useContext, useState, useCallback } from "react";
import type { CanvasNode, CanvasEdge, CanvasLayout } from "@/types/canvas";

export type ViewMode = "visual" | "folder";

interface CanvasState {
  mode: ViewMode;
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  layout: CanvasLayout;
  selectedNodeId: string | null;
  folderPath: string;
  expandedFolders: Set<string>;
}

interface CanvasActions {
  setMode: (mode: ViewMode) => void;
  setNodes: (nodes: CanvasNode[]) => void;
  setEdges: (edges: CanvasEdge[]) => void;
  setLayout: (layout: CanvasLayout) => void;
  selectNode: (id: string | null) => void;
  setFolderPath: (path: string) => void;
  toggleFolder: (path: string) => void;
  expandAll: () => void;
  collapseAll: () => void;
}

const CanvasStateContext = createContext<CanvasState | null>(null);
const CanvasActionsContext = createContext<CanvasActions | null>(null);

export function CanvasProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ViewMode>("visual");
  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const [edges, setEdges] = useState<CanvasEdge[]>([]);
  const [layout, setLayout] = useState<CanvasLayout>("smart");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [folderPath, setFolderPath] = useState<string>("/");
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(["/"]));

  const selectNode = useCallback((id: string | null) => {
    setSelectedNodeId(id);
  }, []);

  const toggleFolder = useCallback((path: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedFolders(new Set(["/"]));
  }, []);

  const collapseAll = useCallback(() => {
    setExpandedFolders(new Set());
  }, []);

  const state: CanvasState = {
    mode,
    nodes,
    edges,
    layout,
    selectedNodeId,
    folderPath,
    expandedFolders,
  };

  const actions: CanvasActions = {
    setMode,
    setNodes,
    setEdges,
    setLayout,
    selectNode,
    setFolderPath,
    toggleFolder,
    expandAll,
    collapseAll,
  };

  return (
    <CanvasStateContext.Provider value={state}>
      <CanvasActionsContext.Provider value={actions}>
        {children}
      </CanvasActionsContext.Provider>
    </CanvasStateContext.Provider>
  );
}

export function useCanvasState() {
  const ctx = useContext(CanvasStateContext);
  if (!ctx) throw new Error("useCanvasState must be used within CanvasProvider");
  return ctx;
}

export function useCanvasActions() {
  const ctx = useContext(CanvasActionsContext);
  if (!ctx) throw new Error("useCanvasActions must be used within CanvasProvider");
  return ctx;
}
