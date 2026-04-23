/** React Query hooks for InkosAI backend data. */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  tapeApi,
  primeApi,
  proposalsApi,
  simulationApi,
  healthApi,
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
  });
}

export function useRecentTape(limit = 20) {
  return useQuery({
    queryKey: ["tape", "recent", limit],
    queryFn: () => tapeApi.getRecent(limit),
    refetchInterval: 10_000, // Auto-refresh every 10s
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["proposals"] }),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["proposals"] }),
  });
}

/* ── Simulation ───────────────────────────────────────────────── */

export function useSimulations(status?: SimulationStatus) {
  return useQuery({
    queryKey: ["simulations", status],
    queryFn: () => simulationApi.list(status),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["simulations"] }),
  });
}

export function useRollbackSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => simulationApi.rollback(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["simulations"] }),
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
