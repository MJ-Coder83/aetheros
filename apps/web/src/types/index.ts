/** Shared TypeScript types for the InkosAI frontend. */

/* ── Tape ─────────────────────────────────────────────────────── */

export interface TapeEntry {
  id: string;
  timestamp: string;
  event_type: string;
  agent_id: string | null;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  commit_id: string | null;
}

/* ── Proposals ────────────────────────────────────────────────── */

export type ModificationType =
  | "skill_addition"
  | "skill_modification"
  | "agent_reconfiguration"
  | "behavior_change"
  | "configuration_update"
  | "architecture_change"
  | "self_modification"
  | "domain_creation";

export type RiskLevel = "low" | "medium" | "high";

export type ProposalStatus =
  | "pending_approval"
  | "approved"
  | "rejected"
  | "implemented";

export interface Proposal {
  id: string;
  title: string;
  modification_type: ModificationType;
  description: string;
  reasoning: string;
  expected_impact: string;
  risk_level: RiskLevel;
  implementation_steps: string[];
  confidence_score: number;
  status: ProposalStatus;
  proposed_by: string;
  reviewer: string | null;
  created_at: string;
  reviewed_at: string | null;
  introspection_snapshot_id: string | null;
  parent_proposal_id: string | null;
}

export interface ProposalSummary {
  id: string;
  title: string;
  modification_type: ModificationType;
  risk_level: RiskLevel;
  confidence_score: number;
  status: ProposalStatus;
  proposed_by: string;
  created_at: string;
}

/* ── Introspection ────────────────────────────────────────────── */

export interface AgentDescriptor {
  agent_id: string;
  name: string;
  capabilities: string[];
  status: string;
  last_seen: string | null;
}

export interface SkillDescriptor {
  skill_id: string;
  name: string;
  version: string;
  description: string;
}

export interface DomainDescriptor {
  domain_id: string;
  name: string;
  description: string;
  agent_count: number;
}

export interface SystemSnapshot {
  timestamp: string;
  system_info: Record<string, string>;
  tape_stats: Record<string, number>;
  recent_tape_entries: TapeEntry[];
  agents: AgentDescriptor[];
  skills: SkillDescriptor[];
  domains: DomainDescriptor[];
  active_worktrees: string[];
  health_status: string;
}

/* ── Simulation ───────────────────────────────────────────────── */

export type SimulationStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "aborted"
  | "rolled_back";

export interface WhatIfScenario {
  id: string;
  name: string;
  description: string;
  scenario_type: string;
  modifications: Record<string, unknown>;
  expected_outcome: string;
  risk_level: RiskLevel;
  source: string;
  created_at: string;
}

export interface SimulationEnvironment {
  skills: SkillDescriptor[];
  agents: AgentDescriptor[];
  domains: DomainDescriptor[];
  metadata: Record<string, unknown>;
}

export interface SimulationResult {
  id: string;
  simulation_run_id: string;
  success: boolean;
  status: SimulationStatus;
  metrics: Record<string, number>;
  decision_trace: Array<Record<string, unknown>>;
  outcome_probabilities: Record<string, number>;
  environment_before: SimulationEnvironment;
  environment_after: SimulationEnvironment;
  error_message: string | null;
  duration_seconds: number;
  completed_at: string;
}

export interface SimulationRun {
  id: string;
  scenario: WhatIfScenario;
  status: SimulationStatus;
  environment_snapshot: SimulationEnvironment;
  result: SimulationResult | null;
  timeout_seconds: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface OutcomeDelta {
  metric: string;
  baseline_value: number;
  simulation_value: number;
  delta: number;
  delta_percent: number;
  improved: boolean;
}

export interface ComparisonReport {
  simulation_run_id: string;
  scenario_name: string;
  deltas: OutcomeDelta[];
  overall_assessment: string;
  recommendation: string;
  summary: string;
}

/* ── Skill Evolution ──────────────────────────────────────────── */

export type EvolutionType =
  | "enhance"
  | "merge"
  | "split"
  | "deprecate"
  | "create";

export interface SkillAnalysis {
  skill_id: string;
  invocation_count: number;
  error_count: number;
  error_rate: number;
  last_invoked: string | null;
  related_skill_ids: string[];
  recommendation: string;
  recommendation_reason: string;
}

/* ── API ───────────────────────────────────────────────────────── */

export interface ApiError {
  detail: string;
}
