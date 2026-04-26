/** Canvas v5 extended types. */
import type { CanvasLayout } from "./canvas";

/* -- Framework Tiers -- */
export type FrameworkTier =
  | "tier_1_browser"
  | "tier_2_high_fidelity"
  | "tier_3_terminal"
  | "tier_4_plugin";

export interface TieredFramework {
  framework: string;
  tier: FrameworkTier;
  label: string;
  description: string;
  icon: string;
  preview_supported: boolean;
  live_editing_supported: boolean;
  code_generation_supported: boolean;
  file_extensions: string[];
}

/* -- NL Edit -- */
export type NLEditType =
  | "move"
  | "resize"
  | "relabel"
  | "restyle"
  | "add"
  | "remove"
  | "connect"
  | "disconnect"
  | "layout"
  | "compound";

export interface NLEditResult {
  edit_id: string;
  instruction: string;
  edit_type: NLEditType;
  confidence: number;
  applied: boolean;
  changes: Record<string, unknown>[];
  error: string | null;
}

/* -- Copilot -- */
export type CopilotSuggestionType =
  | "ux_issue"
  | "layout_optimization"
  | "ab_variant"
  | "auto_optimization"
  | "missing_connection"
  | "redundant_node"
  | "best_practice";

export interface CopilotSuggestion {
  suggestion_id: string;
  suggestion_type: CopilotSuggestionType;
  title: string;
  description: string;
  confidence: number;
  impact: "low" | "medium" | "high";
  target_node_ids: string[];
  auto_applicable: boolean;
  details: Record<string, unknown>;
}

/* -- Simulation Overlay -- */
export interface SimulationMetric {
  metric_name: string;
  value: number;
  unit: string;
  status: "normal" | "warning" | "critical";
  trend: "stable" | "improving" | "degrading";
}

/* -- Tape Overlay -- */
export interface TapeEventEntry {
  event_id: string;
  event_type: string;
  agent_id: string;
  source_node_id: string | null;
  target_node_id: string | null;
  payload: Record<string, unknown>;
  direction: "into" | "out_of" | "through";
}

/* -- Plugin Node -- */
export interface PluginNodeConfig {
  plugin_id: string;
  node_id: string;
  label: string;
  plugin_type: string;
  capabilities: string[];
  command_registry: string[];
  status: string;
  embed_url: string | null;
}

/* -- Versioning -- */
export interface CanvasVersion {
  version: number;
  canvas_id: string;
  domain_id: string;
  commit_message: string;
  author: string;
  created_at: string;
}

export interface CanvasVersionDiff {
  old_version: number;
  new_version: number;
  added_nodes: number;
  removed_nodes: number;
  moved_nodes: number;
}

/* -- Swarm -- */
export type SwarmMode = "quick" | "governed";

export interface QuickSwarmResult {
  swarm_id: string;
  task: string;
  status: string;
  participants: string[];
  results: Record<string, unknown>[];
}

export interface GovernedSwarmResult {
  swarm_id: string;
  task: string;
  status: string;
  proposal_id: string;
  participants: string[];
  proposed_changes: Record<string, unknown>[];
  approval_required: boolean;
}

/* -- Canvas View Mode -- */
export type CanvasViewMode = "visual" | "folder";

/* -- Canvas Operation -- */
export interface CanvasOperation {
  id: string;
  type: string;
  node_id?: string;
  edge_id?: string;
  payload: Record<string, unknown>;
  timestamp: string;
}
