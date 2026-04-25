/** React Query hooks for InkosAI backend data. */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  tapeApi,
  primeApi,
  proposalsApi,
  simulationApi,
  healthApi,
  domainApi,
  type DomainCreationOption,
  type CreationMode,
} from "@/lib/api";
import type { ProposalStatus, SimulationStatus, WhatIfScenario } from "@/types";

/* ── Tape ─────────────────────────────────────────────────────── */

export function useTapeEntries(params?: {
  event_type?: string;
  agent_id?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["tape", "entries", params],
    queryFn: () => tapeApi.getEntries(params),
    refetchInterval: 10_000,
  });
}

export function useRecentTape(limit = 20) {
  return useQuery({
    queryKey: ["tape", "recent", limit],
    queryFn: () => tapeApi.getRecent(limit),
    refetchInterval: 10_000,
  });
}

/* ── Prime Introspection ──────────────────────────────────────── */

export function useSystemSnapshot() {
  return useQuery({
    queryKey: ["prime", "snapshot"],
    queryFn: primeApi.snapshot,
    refetchInterval: 30_000,
  });
}

/* ── Proposals ────────────────────────────────────────────────── */

export function useProposals(status?: ProposalStatus) {
  return useQuery({
    queryKey: ["proposals", status],
    queryFn: () => proposalsApi.list(status),
    refetchInterval: 15_000,
  });
}

export function useProposalSummaries() {
  return useQuery({
    queryKey: ["proposals", "summaries"],
    queryFn: proposalsApi.summarize,
  });
}

export function useApproveProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reviewer }: { id: string; reviewer: string }) =>
      proposalsApi.approve(id, reviewer),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["proposals"] });
      toast.success("Proposal approved", {
        description: "The proposal has been approved and can now be implemented.",
      });
    },
    onError: (error) => {
      toast.error("Failed to approve proposal", {
        description: error.message,
      });
    },
  });
}

export function useRejectProposal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      reviewer,
      reason,
    }: {
      id: string;
      reviewer: string;
      reason?: string;
    }) => proposalsApi.reject(id, reviewer, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["proposals"] });
      toast.success("Proposal rejected", {
        description: "The proposal has been rejected.",
      });
    },
    onError: (error) => {
      toast.error("Failed to reject proposal", {
        description: error.message,
      });
    },
  });
}

/* ── Simulation ───────────────────────────────────────────────── */

export function useSimulations(status?: SimulationStatus) {
  return useQuery({
    queryKey: ["simulations", status],
    queryFn: () => simulationApi.list(status),
    refetchInterval: 8_000, // Poll more often for running sims
  });
}

export function useSimulationScenarios() {
  return useQuery({
    queryKey: ["simulations", "scenarios"],
    queryFn: simulationApi.scenarios,
  });
}

export function useRunSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      scenario,
      timeout,
    }: {
      scenario: WhatIfScenario;
      timeout?: number;
    }) => simulationApi.run(scenario, timeout),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["simulations"] });
      toast.success("Simulation started", {
        description: `Running "${variables.scenario.name}"...`,
      });
    },
    onError: (error) => {
      toast.error("Simulation failed", {
        description: error.message,
      });
    },
  });
}

export function useRollbackSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => simulationApi.rollback(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulations"] });
      toast.success("Simulation rolled back", {
        description: "The simulation has been rolled back. No side effects on production.",
      });
    },
    onError: (error) => {
      toast.error("Rollback failed", {
        description: error.message,
      });
    },
  });
}

export function useComparisonReport(runId: string | null) {
  return useQuery({
    queryKey: ["simulations", "compare", runId],
    queryFn: () => simulationApi.compare(runId!),
    enabled: runId !== null,
  });
}

/* ── Health ───────────────────────────────────────────────────── */

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: healthApi.check,
    refetchInterval: 15_000,
  });
}

/* ── Domain Creation ──────────────────────────────────────────── */

export function useDomains() {
  return useQuery({
    queryKey: ["domains"],
    queryFn: domainApi.list,
    refetchInterval: 30_000,
  });
}

export function useDomain(domainId: string | null) {
  return useQuery({
    queryKey: ["domains", domainId],
    queryFn: () => domainApi.get(domainId!),
    enabled: domainId !== null,
  });
}

export function useDomainBlueprints() {
  return useQuery({
    queryKey: ["domain-blueprints"],
    queryFn: domainApi.listBlueprints,
  });
}

export function useCreateDomain() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      description: string;
      domain_name?: string;
      creation_mode?: CreationMode;
      created_by?: string;
    }) => domainApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["domains"] });
      qc.invalidateQueries({ queryKey: ["domain-blueprints"] });
      qc.invalidateQueries({ queryKey: ["prime", "snapshot"] });
      toast.success("Domain created", {
        description: "Your domain blueprint has been generated and submitted for approval.",
      });
    },
    onError: (error: Error) => {
      toast.error("Failed to create domain", { description: error.message });
    },
  });
}

export function useOneClickCreateDomain() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      description: string;
      domain_name?: string;
      creation_option?: DomainCreationOption;
      creation_mode?: CreationMode;
      created_by?: string;
    }) => domainApi.oneClickCreate(body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["domains"] });
      qc.invalidateQueries({ queryKey: ["domain-blueprints"] });
      qc.invalidateQueries({ queryKey: ["prime", "snapshot"] });
      const hasCanvas = data.starter_canvas !== null;
      toast.success("Domain created", {
        description: hasCanvas
          ? "Your domain with starter canvas has been generated and submitted for approval."
          : "Your domain blueprint has been generated and submitted for approval.",
      });
    },
    onError: (error: Error) => {
      toast.error("Failed to create domain", { description: error.message });
    },
  });
}

export function useRegisterDomain() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ blueprintId, reviewer }: { blueprintId: string; reviewer?: string }) =>
      domainApi.register(blueprintId, reviewer),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["domains"] });
      qc.invalidateQueries({ queryKey: ["prime", "snapshot"] });
      toast.success("Domain registered", {
        description: "The domain has been registered and is now active.",
      });
    },
    onError: (error: Error) => {
      toast.error("Failed to register domain", { description: error.message });
    },
  });
}

/* ── Explainability ──────────────────────────────────────────── */
import { explainApi } from "@/lib/api";
import type { ActionType } from "@/types";

export function useExplanations(actionType?: ActionType) {
  return useQuery({
    queryKey: ["explainability", actionType],
    queryFn: () => explainApi.list(actionType),
    refetchInterval: 30_000,
  });
}

export function useExplanation(id: string | null) {
  return useQuery({
    queryKey: ["explainability", id],
    queryFn: () => explainApi.get(id!),
    enabled: id !== null,
  });
}

export function useGenerateExplanation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      action_id: string;
      action_type: ActionType;
      context?: Record<string, unknown>;
    }) => explainApi.generate(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["explainability"] });
      toast.success("Explanation generated");
    },
    onError: (error: Error) => {
      toast.error("Failed to generate explanation", { description: error.message });
    },
  });
}

export function useDecisionTrace() {
  return useMutation({
    mutationFn: (body: {
      action_id: string;
      action_type?: ActionType;
      context?: Record<string, unknown>;
    }) => explainApi.trace(body),
    onError: (error: Error) => {
      toast.error("Failed to get decision trace", { description: error.message });
    },
  });
}

export function useKeyFactors() {
  return useMutation({
    mutationFn: (body: {
      action_id: string;
      action_type?: ActionType;
      context?: Record<string, unknown>;
      top_n?: number;
    }) => explainApi.factors(body),
    onError: (error: Error) => {
      toast.error("Failed to highlight key factors", { description: error.message });
    },
  });
}
