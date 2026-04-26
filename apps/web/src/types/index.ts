/** Shared TypeScript types for the InkosAI frontend. */

/* ── Tape ─────────────────────────────────────────────────────── */

export interface TapeEntry {
  id: string;
  timestamp: string;
  event_type: string;
  agent_id: string | null;
  payload: Record<string, string | number | boolean | null>;
  metadata: Record<string, string | number | boolean | null>;
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
  health_status: "healthy" | "degraded" | "unhealthy" | "unknown";
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
  modifications: Record<string, string | number | boolean | null>;
  expected_outcome: string;
  risk_level: RiskLevel;
  source: string;
  created_at: string;
}

export interface SimulationEnvironment {
  skills: SkillDescriptor[];
  agents: AgentDescriptor[];
  domains: DomainDescriptor[];
  metadata: Record<string, string | number | boolean | null>;
}

export interface SimulationResult {
  id: string;
  simulation_run_id: string;
  success: boolean;
  status: SimulationStatus;
  metrics: Record<string, number>;
  decision_trace: Array<Record<string, string | number | boolean | null>>;
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

/* -- Explainability ------------------------------------------------- */
export type ActionType =
  | 'proposal_created' | 'proposal_approved' | 'proposal_rejected'
  | 'proposal_implemented' | 'skill_evolution' | 'skill_created'
  | 'skill_deprecated' | 'skill_merged' | 'skill_split'
  | 'skill_enhanced' | 'simulation_run' | 'simulation_comparison'
  | 'debate_started' | 'debate_round' | 'debate_concluded'
  | 'tape_entry' | 'introspection' | 'system_action';

export type FactorCategory =
  | 'data_driven' | 'heuristic' | 'risk_assessment'
  | 'stakeholder' | 'historical' | 'system_state'
  | 'constraint' | 'confidence';

export type AlternativeOutcome =
  | 'superior' | 'equivalent' | 'inferior' | 'incomparable';

export interface KeyFactor {
  name: string;
  description: string;
  category: FactorCategory;
  importance: number;
  evidence: string[];
  direction: string;
}

export interface DecisionStep {
  step_number: number;
  action: string;
  rationale: string;
  data_sources: string[];
  confidence: number;
  timestamp: string | null;
}

export interface DecisionTrace {
  action_id: string;
  action_type: ActionType;
  steps: DecisionStep[];
  total_confidence: number;
  data_sources_used: string[];
  assumptions: string[];
  limitations: string[];
}

export interface Alternative {
  action_id: string;
  label: string;
  description: string;
  score: number;
  outcome: AlternativeOutcome;
  pros: string[];
  cons: string[];
  key_differences: string[];
}

export interface AlternativeComparison {
  action_id: string;
  chosen_label: string;
  chosen_score: number;
  alternatives: Alternative[];
  summary: string;
  trade_offs: string[];
}

export interface Explanation {
  id: string;
  action_id: string;
  action_type: ActionType;
  technical_summary: string;
  simplified_summary: string;
  key_factors: KeyFactor[];
  decision_trace: DecisionTrace | null;
  alternative_comparison: AlternativeComparison | null;
  confidence: number;
  risk_level: string;
  related_tape_entries: string[];
  metadata: Record<string, string | number | boolean | null>;
  created_at: string;
}

export interface ApiError {
  detail: string;
}

/* ── Intelligence Profile & User Profile ───────────────────── */
export type ExpertiseLevel = "novice" | "intermediate" | "advanced" | "expert";
export type InteractionType =
  | "query" | "command" | "approval" | "rejection" | "proposal"
  | "simulation" | "debate" | "browser" | "feedback"
  | "domain_created" | "plan_created" | "debate_started";
export type PreferenceCategory =
  | "response_detail" | "automation_level" | "notification_frequency"
  | "risk_tolerance" | "workflow_style" | "explanation_depth"
  | "suggestion_frequency";
export type ProfileStatus = "active" | "archived" | "suspended";
export type WorkingStyle =
  | "methodical" | "exploratory" | "collaborative"
  | "independent" | "visual" | "textual";
export type AutomationPreference =
  | "manual" | "assisted" | "semi_automated" | "fully_automated";
export type CommunicationStyle =
  | "concise" | "detailed" | "technical" | "conversational";

export interface DomainExpertise {
  domain_id: string;
  level: ExpertiseLevel;
  score: number;
  interaction_count: number;
  total_depth: number;
  avg_depth: number;
  last_interaction: string | null;
  skills_used: string[];
  preferred_workflows: string[];
}

export interface UserPreference {
  category: PreferenceCategory;
  value: number;
  explicit_value: number | null;
  inferred_value: number;
  confidence: number;
  last_updated: string;
}

export interface InteractionSummary {
  total_interactions: number;
  interactions_by_type: Record<string, number>;
  interactions_by_domain: Record<string, number>;
  avg_depth: number;
  peak_depth: number;
  last_interaction: string | null;
  approval_rate: number;
  most_active_hour: number;
  daily_streak: number;
}

/** Embedded intelligence tracking within UserProfile. */
export interface IntelligenceProfile {
  domain_expertise: Record<string, DomainExpertise>;
  preferences: Record<string, UserPreference>;
  interaction_summary: InteractionSummary;
  behavioural_signals: Record<string, unknown>;
  adaptation_count: number;
  snapshot_id: string | null;
}

export interface ProfileSnapshot {
  id: string;
  profile_id: string;
  profile_data: Record<string, unknown>;
  reason: string;
  created_at: string;
}

export interface WorkingStyleConfig {
  primary_style: WorkingStyle;
  secondary_styles: WorkingStyle[];
  preferred_session_length: number;
  peak_hours: number[];
  timezone: string;
  automation_preference: AutomationPreference;
  communication_style: CommunicationStyle;
  context_retention: number;
}

export interface UserGoal {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: number;
  status: string;
  created_at: string;
  updated_at: string;
  target_date: string | null;
  completed_at: string | null;
  progress: number;
  metadata: Record<string, unknown>;
}

export interface LearnedSkill {
  skill_id: string;
  name: string;
  category: string;
  proficiency: number;
  first_observed: string;
  last_used: string;
  usage_count: number;
  verified: boolean;
  source: string;
}

export interface InteractionPattern {
  pattern_type: string;
  pattern_value: string;
  frequency: number;
  confidence: number;
  first_observed: string;
  last_observed: string;
  is_active: boolean;
}

export interface HistorySummary {
  total_sessions: number;
  total_interactions: number;
  total_domains: number;
  total_proposals: number;
  total_approvals: number;
  total_rejections: number;
  avg_session_duration: number;
  favorite_domains: string[];
  common_patterns: string[];
  last_session_at: string | null;
  summary_generated_at: string;
}

export interface UserPreferenceSetting {
  key: string;
  value: unknown;
  category: string;
  is_explicit: boolean;
  confidence: number;
  created_at: string;
  updated_at: string;
}

/** Complete user profile for Prime personalization. */
export interface UserProfile {
  id: string;
  user_id: string;
  version: number;
  status: ProfileStatus;
  display_name: string;
  email: string;
  bio: string;
  working_style: WorkingStyleConfig;
  preferences: Record<string, UserPreferenceSetting>;
  intelligence: IntelligenceProfile;
  goals: UserGoal[];
  learned_skills: Record<string, LearnedSkill>;
  interaction_patterns: InteractionPattern[];
  history_summary: HistorySummary;
  storage_backend: string;
  folder_tree_path: string;
  aethergit_commit_id: string | null;
  created_at: string;
  updated_at: string;
  last_sync_at: string | null;
}

export interface RecommendationContext {
  user_id: string;
  expertise_level: string;
  top_domains: Array<{ domain_id: string; level: string; score: number }>;
  preferences: Record<string, number>;
  interaction_count: number;
  avg_depth: number;
  approval_rate: number;
  adaptation_count: number;
  working_style: string;
  automation_preference: string;
  communication_style: string;
  active_goals: number;
  total_skills: number;
}

export interface ProfileSummary {
  user_id: string;
  display_name: string;
  working_style: string;
  automation_preference: string;
  total_goals: number;
  active_goals: number;
  total_skills: number;
  verified_skills: number;
  total_preferences: number;
  total_patterns: number;
  total_sessions: number;
  favorite_domains: string[];
  last_sync: string | null;
}

/* ── Plugin System & Marketplace ────────────────────────────── */

export type PluginPermission =
  | "folder_tree_read"
  | "folder_tree_write"
  | "tape_read"
  | "tape_write"
  | "agent_communicate"
  | "canvas_read"
  | "canvas_write"
  | "domain_read"
  | "network_access"
  | "system_config";

export type PluginStatus =
  | "installed"
  | "enabled"
  | "disabled"
  | "error"
  | "pending_install";

export type MarketplacePluginStatus =
  | "published"
  | "under_review"
  | "deprecated"
  | "removed";

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  homepage: string | null;
  repository: string | null;
  permissions: PluginPermission[];
  entry_point: string;
  min_platform_version: string;
  max_platform_version: string | null;
  tags: string[];
  category: string;
  icon: string | null;
}

export interface InstalledPlugin {
  id: string;
  manifest: PluginManifest;
  status: PluginStatus;
  installed_at: string;
  updated_at: string;
  enabled: boolean;
  install_path: string;
  last_error: string | null;
}

export interface MarketplacePlugin {
  id: string;
  manifest: PluginManifest;
  status: MarketplacePluginStatus;
  downloads: number;
  rating_avg: number;
  rating_count: number;
  published_at: string;
  updated_at: string;
  featured: boolean;
  verified: boolean;
}

export interface PluginRating {
  user_id: string;
  plugin_id: string;
  score: number;
  review: string | null;
  created_at: string;
}

export interface PluginInstallRequest {
  plugin_id: string;
  version: string;
  granted_permissions: PluginPermission[];
  user_id: string;
}

export interface PluginInstallResult {
  success: boolean;
  plugin: InstalledPlugin | null;
  message: string;
  errors: string[];
}

export interface MarketplaceSearchParams {
  query?: string;
  category?: string;
  tags?: string[];
  sort_by?: "downloads" | "rating" | "newest" | "name";
  limit?: number;
  offset?: number;
}

// ── Settings / Provider Selector ──

export interface ProviderInfo {
  provider_id: string;
  display_name: string;
  base_url: string;
  icon: string | null;
  models: string[];
  has_key_configured: boolean;
  selected_model: string | null;
}

export interface Settings {
  active_provider_id: string;
  active_model_id: string;
  provider_keys: Record<string, string>;
  default_models: Record<string, string>;
}

export interface ConnectionTestResult {
  provider_id: string;
  success: boolean;
  message: string;
  model_count: number | null;
}
