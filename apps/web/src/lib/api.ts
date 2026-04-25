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