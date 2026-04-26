/** InkosAI API client — typed fetch wrapper.
 *
 *  In development, all requests go through /api/* proxy to avoid CORS.
 *  Set NEXT_PUBLIC_API_URL for the backend if different from default.
 */

const API_URL = ""; // Requests go through Next.js API proxy

// Direct backend URL — referenced when bypassing the Next.js proxy.
// const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiClientError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new ApiClientError(res.status, body);
  }

  return res.json() as Promise<T>;
}

/* ── Tape ─────────────────────────────────────────────────────── */

import type { TapeEntry } from "@/types";

export const tapeApi = {
  getEntries(params?: {
    event_type?: string;
    agent_id?: string;
    limit?: number;
  }): Promise<TapeEntry[]> {
    const search = new URLSearchParams();
    if (params?.event_type) search.set("event_type", params.event_type);
    if (params?.agent_id) search.set("agent_id", params.agent_id);
    if (params?.limit) search.set("limit", String(params.limit));
    const qs = search.toString();
    return request(`/api/tape/entries${qs ? `?${qs}` : ""}`);
  },

  getEntry(id: string): Promise<TapeEntry> {
    return request(`/api/tape/entries/${id}`);
  },

  getRecent(limit = 20): Promise<TapeEntry[]> {
    return request(`/api/tape/entries?limit=${limit}`);
  },
};

/* ── Prime Introspection ──────────────────────────────────────── */

import type { SystemSnapshot } from "@/types";

export const primeApi = {
  snapshot(): Promise<SystemSnapshot> {
    return request("/api/prime/snapshot");
  },
};

/* ── Proposals ────────────────────────────────────────────────── */

import type {
  Proposal,
  ProposalStatus,
  ProposalSummary,
} from "@/types";

export const proposalsApi = {
  list(status?: ProposalStatus): Promise<Proposal[]> {
    const qs = status ? `?status=${status}` : "";
    return request(`/api/prime/proposals${qs}`);
  },

  get(id: string): Promise<Proposal> {
    return request(`/api/prime/proposals/${id}`);
  },

  approve(id: string, reviewer: string): Promise<Proposal> {
    return request(`/api/prime/proposals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ reviewer }),
    });
  },

  reject(id: string, reviewer: string, reason?: string): Promise<Proposal> {
    return request(`/api/prime/proposals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reviewer, reason }),
    });
  },

  summarize(): Promise<ProposalSummary[]> {
    return request("/api/prime/proposals/summarize");
  },
};

/* ── Skill Evolution ──────────────────────────────────────────── */

import type { SkillAnalysis } from "@/types";

// Extend types for skill evolution endpoints
interface SkillEvolutionProposalLocal {
  id: string;
  proposal_id: string;
  evolution_type: string;
  target_skill_ids: string[];
  new_skill_descriptor: unknown | null;
  before_snapshot: unknown[];
  reasoning: string;
  created_at: string;
}

export const skillEvolutionApi = {
  analyze(): Promise<SkillAnalysis[]> {
    return request("/api/prime/skill-evolution/analyze");
  },

  proposals(): Promise<SkillEvolutionProposalLocal[]> {
    return request("/api/prime/skill-evolution/proposals");
  },
};

/* ── Simulation ───────────────────────────────────────────────── */

import type {
  ComparisonReport,
  SimulationRun,
  SimulationStatus,
  WhatIfScenario,
} from "@/types";

export const simulationApi = {
  list(status?: SimulationStatus): Promise<SimulationRun[]> {
    const qs = status ? `?status=${status}` : "";
    return request(`/api/simulation/runs${qs}`);
  },

  get(id: string): Promise<SimulationRun> {
    return request(`/api/simulation/runs/${id}`);
  },

  run(scenario: WhatIfScenario, timeout = 60): Promise<SimulationRun> {
    return request("/api/simulation/run", {
      method: "POST",
      body: JSON.stringify({ scenario, timeout_seconds: timeout }),
    });
  },

  compare(id: string): Promise<ComparisonReport> {
    return request(`/api/simulation/runs/${id}/compare`);
  },

  rollback(id: string): Promise<unknown> {
    return request(`/api/simulation/runs/${id}/rollback`, { method: "POST" });
  },

  scenarios(): Promise<WhatIfScenario[]> {
    return request("/api/simulation/scenarios");
  },
};

/* ── Health ───────────────────────────────────────────────────── */

export const healthApi = {
  check(): Promise<{ status: string }> {
    return request("/api/health");
  },
};

/* ── Domain Creation ────────────────────────────────────────────── */

export type DomainCreationOption = "domain_only" | "domain_with_starter_canvas";
export type CreationMode = "automatic" | "human_guided" | "hybrid";

interface DomainBlueprint {
  id: string;
  domain_name: string;
  domain_id: string;
  description: string;
  source_description: string;
  agents: Array<{
    agent_id: string;
    name: string;
    role: string;
    goal: string;
    backstory: string;
    capabilities: string[];
    tools: string[];
  }>;
  skills: Array<{
    skill_id: string;
    name: string;
    description: string;
    version: string;
    is_reused: boolean;
    source_domain: string | null;
  }>;
  workflows: Array<{
    workflow_id: string;
    name: string;
    workflow_type: string;
    description: string;
    agent_ids: string[];
    steps: string[];
  }>;
  config: {
    max_agents: number;
    max_concurrent_tasks: number;
    requires_human_approval: boolean;
    data_retention_days: number;
    priority_level: string;
    custom_settings: Record<string, unknown>;
  };
  creation_mode: CreationMode;
  status: string;
  proposal_id: string | null;
  created_by: string;
  created_at: string;
  validation_errors: string[];
  validation_warnings: string[];
}

interface OneClickDomainCreationResult {
  blueprint: DomainBlueprint;
  folder_tree: unknown | null;
  starter_canvas: unknown | null;
  canvas_id: string | null;
  proposal_id: string | null;
  registered: boolean;
  domain: unknown | null;
  message: string;
}

export const domainApi = {
  create(body: {
    description: string;
    domain_name?: string;
    creation_mode?: CreationMode;
    created_by?: string;
  }): Promise<DomainBlueprint> {
    return request("/api/domains/create", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  oneClickCreate(body: {
    description: string;
    domain_name?: string;
    creation_option?: DomainCreationOption;
    creation_mode?: CreationMode;
    created_by?: string;
  }): Promise<OneClickDomainCreationResult> {
    return request("/api/domains/one-click", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  generateBlueprint(body: {
    description: string;
    domain_name?: string;
    creation_mode?: CreationMode;
    created_by?: string;
  }): Promise<DomainBlueprint> {
    return request("/api/domains/blueprint", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  register(blueprintId: string, reviewer?: string): Promise<unknown> {
    return request("/api/domains/register", {
      method: "POST",
      body: JSON.stringify({ blueprint_id: blueprintId, reviewer }),
    });
  },

  list(): Promise<Array<{ domain_id: string; name: string; description: string; agent_count: number }>> {
    return request("/api/domains");
  },

  get(domainId: string): Promise<{ domain_id: string; name: string; description: string; agent_count: number }> {
    return request(`/api/domains/${domainId}`);
  },

  listBlueprints(): Promise<DomainBlueprint[]> {
    return request("/api/domains/blueprints");
  },

  getBlueprint(blueprintId: string): Promise<DomainBlueprint> {
    return request(`/api/domains/blueprints/${blueprintId}`);
  },
};


/* ── Explainability ────────────────────────────────────────────── */
import type { Explanation, ActionType } from "@/types";

export const explainApi = {
  generate(body: {
    action_id: string;
    action_type: ActionType;
    context?: Record<string, unknown>;
  }): Promise<Explanation> {
    return request("/api/explain/generate", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  trace(body: {
    action_id: string;
    action_type?: ActionType;
    context?: Record<string, unknown>;
  }): Promise<Record<string, unknown>> {
    return request("/api/explain/trace", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  factors(body: {
    action_id: string;
    action_type?: ActionType;
    context?: Record<string, unknown>;
    top_n?: number;
  }): Promise<Record<string, unknown>[]> {
    return request("/api/explain/factors", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  compare(body: {
    action_id: string;
    alternatives: Record<string, unknown>[];
    action_type?: ActionType;
    context?: Record<string, unknown>;
  }): Promise<Record<string, unknown>> {
    return request("/api/explain/compare", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  get(id: string): Promise<Explanation> {
    return request(`/api/explain/${id}`);
  },

  list(actionType?: ActionType): Promise<Explanation[]> {
    const qs = actionType ? `?action_type=${actionType}` : "";
    return request(`/api/explain${qs}`);
  },
};

/* ── Intelligence Profile ────────────────────────────────────── */

import type {
  UserProfile,
  ProfileSummary,
  ProfileSnapshot,
  RecommendationContext,
  
  InteractionType,
  PreferenceCategory,
} from "@/types";

export const profileApi = {
  get(userId: string): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}`);
  },

  getOrCreate(userId: string): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}`, { method: "POST" });
  },

  list(): Promise<UserProfile[]> {
    return request("/api/profiles");
  },

  recordInteraction(body: {
    user_id: string;
    interaction_type: InteractionType;
    domain?: string;
    depth?: number;
    approved?: boolean;
    metadata?: Record<string, unknown>;
  }): Promise<UserProfile> {
    return request("/api/profiles/interactions", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  setPreference(body: {
    user_id: string;
    category: PreferenceCategory;
    value: number;
  }): Promise<UserProfile> {
    return request("/api/profiles/preferences", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  getEffectivePreference(userId: string, category: string): Promise<{ category: string; value: number }> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/preferences/${encodeURIComponent(category)}`);
  },

  createSnapshot(userId: string, reason?: string): Promise<ProfileSnapshot> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/snapshots`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? "" }),
    });
  },

  listSnapshots(userId: string): Promise<ProfileSnapshot[]> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/snapshots`);
  },

  rollback(userId: string, snapshotId: string): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/rollback/${encodeURIComponent(snapshotId)}`, {
      method: "POST",
    });
  },

  getDomainSummary(userId: string): Promise<Record<string, { level: string; score: number }>> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/domains`);
  },

  getRecommendationContext(userId: string): Promise<RecommendationContext> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/context`);
  },

  merge(sourceUserId: string, targetUserId: string): Promise<UserProfile> {
    return request("/api/profiles/merge", {
      method: "POST",
      body: JSON.stringify({ source_user_id: sourceUserId, target_user_id: targetUserId }),
    });
  },

  archive(userId: string): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/archive`, { method: "POST" });
  },

  suspend(userId: string): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/suspend`, { method: "POST" });
  },

  reactivate(userId: string): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/reactivate`, { method: "POST" });
  },

  // ── UserProfile endpoints ──────────────────────────────────
  getSummary(userId: string): Promise<ProfileSummary> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/summary`);
  },

  updateDetails(userId: string, body: { display_name?: string; email?: string; bio?: string }): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/details`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  setUserPreference(userId: string, key: string, value: unknown, category: string = "general"): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/user-preferences`, {
      method: "POST",
      body: JSON.stringify({ key, value, category }),
    });
  },

  updateWorkingStyle(userId: string, body: Record<string, unknown>): Promise<UserProfile> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/working-style`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  addGoal(userId: string, title: string, description: string = "", category: string = "general", priority: number = 3): Promise<unknown> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/goals`, {
      method: "POST",
      body: JSON.stringify({ title, description, category, priority }),
    });
  },

  listGoals(userId: string, status?: string): Promise<unknown[]> {
    const qs = status ? `?status=${status}` : "";
    return request(`/api/profiles/${encodeURIComponent(userId)}/goals${qs}`);
  },

  completeGoal(userId: string, goalId: string): Promise<unknown> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/goals/${encodeURIComponent(goalId)}/complete`, { method: "POST" });
  },

  addSkill(userId: string, skillId: string, name: string, proficiency: number = 0.0): Promise<unknown> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/skills`, {
      method: "POST",
      body: JSON.stringify({ skill_id: skillId, name, proficiency }),
    });
  },

  listSkills(userId: string, category?: string): Promise<unknown[]> {
    const qs = category ? `?category=${category}` : "";
    return request(`/api/profiles/${encodeURIComponent(userId)}/skills${qs}`);
  },

  recordPattern(userId: string, patternType: string, patternValue: string, confidence: number = 0.5): Promise<unknown> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/patterns`, {
      method: "POST",
      body: JSON.stringify({ pattern_type: patternType, pattern_value: patternValue, confidence }),
    });
  },

  recordSession(userId: string, duration: number, interactions: number = 0, domains?: string[]): Promise<unknown> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/sessions`, {
      method: "POST",
      body: JSON.stringify({ duration, interactions, domains }),
    });
  },

  syncToAethergit(userId: string, commitMessage: string = "Update user profile"): Promise<{ commit_id: string | null }> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/sync`, {
      method: "POST",
      body: JSON.stringify({ commit_message: commitMessage }),
    });
  },

  exportProfile(userId: string): Promise<Record<string, unknown>> {
    return request(`/api/profiles/${encodeURIComponent(userId)}/export`);
  },
};

/* ── Marketplace ────────────────────────────────────────────── */

import type {
  MarketplacePlugin,
  InstalledPlugin,
  PluginInstallResult,
  PluginRating,
  MarketplaceSearchParams,
  PluginPermission,
} from "@/types";

export const marketplaceApi = {
  discover(params?: MarketplaceSearchParams): Promise<MarketplacePlugin[]> {
    const search = new URLSearchParams();
    if (params?.query) search.set("query", params.query);
    if (params?.category) search.set("category", params.category);
    if (params?.tags?.length) search.set("tags", params.tags.join(","));
    if (params?.sort_by) search.set("sort_by", params.sort_by);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.offset) search.set("offset", String(params.offset));
    const qs = search.toString();
    return request(`/api/marketplace/plugins${qs ? `?${qs}` : ""}`);
  },

  getPlugin(pluginId: string): Promise<MarketplacePlugin> {
    return request(`/api/marketplace/plugins/${encodeURIComponent(pluginId)}`);
  },

  install(pluginId: string, body: {
    version: string;
    granted_permissions: PluginPermission[];
    user_id: string;
  }): Promise<PluginInstallResult> {
    return request(`/api/marketplace/plugins/${encodeURIComponent(pluginId)}/install`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  uninstall(pluginId: string): Promise<{ success: boolean; message: string }> {
    return request(`/api/marketplace/plugins/${encodeURIComponent(pluginId)}/uninstall`, {
      method: "POST",
    });
  },

  listInstalled(): Promise<InstalledPlugin[]> {
    return request("/api/marketplace/installed");
  },

  rate(pluginId: string, body: { score: number; review?: string; user_id: string }): Promise<PluginRating> {
    return request(`/api/marketplace/plugins/${encodeURIComponent(pluginId)}/rate`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
};