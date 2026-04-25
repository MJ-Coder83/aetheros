/** Canvas-specific TypeScript types. */

/* ── Nodes ────────────────────────────────────────────────────── */

export type NodeType =
  | "agent"
  | "skill"
  | "workflow"
  | "domain"
  | "browser"
  | "terminal"
  | "plugin"
  | "group";

export type NodeStatus = "active" | "idle" | "error" | "offline" | "building";

export interface CanvasNode {
  id: string;
  type: NodeType;
  label: string;
  description?: string;
  status: NodeStatus;
  x: number;
  y: number;
  width: number;
  height: number;
  metadata: Record<string, string | number | boolean | null>;
  folderPath?: string;
  children?: string[];
  parentId?: string | null;
}

/* ── Edges ────────────────────────────────────────────────────── */

export type EdgeType = "dependency" | "flow" | "data" | "control" | "group";

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label?: string;
  metadata: Record<string, string | number | boolean | null>;
}

/* ── Layout ───────────────────────────────────────────────────── */

export type CanvasLayout =
  | "layered"
  | "hub-and-spoke"
  | "clustered"
  | "linear"
  | "smart";

/* ── Folder Tree ──────────────────────────────────────────────── */

export interface FolderItem {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FolderItem[];
  size?: number;
  modifiedAt?: string;
  metadata?: Record<string, string | number | boolean | null>;
}

/* ── Canvas API ───────────────────────────────────────────────── */

export interface CanvasSnapshot {
  id: string;
  name: string;
  domainId: string;
  nodes: CanvasNode[];
  edges: CanvasEdge[];
  layout: CanvasLayout;
  folderTree: FolderItem;
  createdAt: string;
  updatedAt: string;
}

export interface CanvasOperation {
  id: string;
  type: string;
  nodeId?: string;
  edgeId?: string;
  payload: Record<string, unknown>;
  timestamp: string;
}
