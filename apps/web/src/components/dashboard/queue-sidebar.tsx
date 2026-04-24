"use client";

import { useState } from "react";
import { FileCheck, FlaskConical } from "lucide-react";
import type { Proposal, SimulationRun } from "@/types";
import { useApproveProposal, useRejectProposal } from "@/hooks/use-api";

interface QueueSidebarProps {
  proposals: Proposal[];
  simulations: SimulationRun[];
  isLoading: boolean;
}

type Tab = "pending" | "running";

function confidenceColor(score: number): string {
  if (score < 0.5) return "bg-red-400";
  if (score < 0.7) return "bg-amber-400";
  return "bg-emerald-400";
}

function confidenceTextColor(score: number): string {
  if (score < 0.5) return "text-red-400";
  if (score < 0.7) return "text-amber-400";
  return "text-emerald-400";
}

function riskColor(risk: string): string {
  if (risk === "low") return "bg-emerald-400/10 text-emerald-400 border-emerald-400/20";
  if (risk === "medium") return "bg-amber-400/10 text-amber-400 border-amber-400/20";
  return "bg-red-400/10 text-red-400 border-red-400/20";
}

function ProposalCard({ proposal }: { proposal: Proposal }) {
  const approveMutation = useApproveProposal();
  const rejectMutation = useRejectProposal();

  return (
    <div className="bg-card rounded border border-border p-3">
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-medium text-foreground leading-tight flex-1 min-w-0 pr-2">
          {proposal.title}
        </h4>
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ml-2 ${riskColor(proposal.risk_level)}`}
        >
          {proposal.risk_level.toUpperCase()} RISK
        </span>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] text-muted-foreground">Confidence</span>
        <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${confidenceColor(proposal.confidence_score)}`}
            style={{ width: `${Math.round(proposal.confidence_score * 100)}%` }}
          />
        </div>
        <span
          className={`text-[10px] font-medium ${confidenceTextColor(proposal.confidence_score)}`}
          style={{ fontFamily: "var(--font-plex-mono), monospace" }}
        >
          {Math.round(proposal.confidence_score * 100)}%
        </span>
      </div>

      <div className="flex gap-2">
        <button
          className="flex-1 py-1.5 text-xs font-medium rounded bg-emerald-400/10 text-emerald-400 border border-emerald-400/20 hover:bg-emerald-400/20 transition-colors"
          onClick={() =>
            approveMutation.mutate({ id: proposal.id, reviewer: "human" })
          }
        >
          Approve
        </button>
        <button
          className="flex-1 py-1.5 text-xs font-medium rounded bg-red-400/10 text-red-400 border border-red-400/20 hover:bg-red-400/20 transition-colors"
          onClick={() =>
            rejectMutation.mutate({ id: proposal.id, reviewer: "human" })
          }
        >
          Reject
        </button>
      </div>
    </div>
  );
}

function SimulationCard({ simulation }: { simulation: SimulationRun }) {
  const elapsed = simulation.started_at
    ? Math.floor(
        (Date.now() - new Date(simulation.started_at).getTime()) / 1000
      )
    : 0;
  const remaining = Math.max(0, simulation.timeout_seconds - elapsed);

  return (
    <div className="bg-card rounded border border-border p-3">
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-medium text-foreground leading-tight flex-1 min-w-0 pr-2">
          {simulation.scenario.name}
        </h4>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-inkos-cyan/10 text-inkos-cyan border border-inkos-cyan/20 shrink-0 ml-2">
          RUNNING
        </span>
      </div>

      <div className="mb-2">
        <div className="h-1 bg-secondary rounded-full overflow-hidden">
          <div
            className="h-full bg-inkos-cyan rounded-full animate-pulse"
            style={{
              width: `${Math.min(100, (elapsed / simulation.timeout_seconds) * 100)}%`,
            }}
          />
        </div>
      </div>

      <span className="text-[10px] text-muted-foreground">
        ETA: {remaining}s · Timeout: {simulation.timeout_seconds}s
      </span>
    </div>
  );
}

export function QueueSidebar({
  proposals,
  simulations,
  isLoading,
}: QueueSidebarProps) {
  const [tab, setTab] = useState<Tab>("pending");

  const pendingProposals = proposals.filter(
    (p) => p.status === "pending_approval"
  );
  const runningSims = simulations.filter((s) => s.status === "running");

  return (
    <div className="w-[380px] p-4 pl-2 flex flex-col shrink-0">
      <div className="flex gap-1 mb-3 shrink-0 bg-card rounded p-1 border border-border">
        <button
          className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
            tab === "pending"
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setTab("pending")}
        >
          Pending ({pendingProposals.length})
        </button>
        <button
          className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
            tab === "running"
              ? "bg-secondary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setTab("running")}
        >
          Running ({runningSims.length})
        </button>
      </div>

      <div className="flex-1 flex flex-col gap-3 overflow-y-auto">
        {tab === "pending" ? (
          isLoading ? (
            Array.from({ length: 2 }).map((_, i) => (
              <div
                key={i}
                className="bg-card rounded border border-border p-3 h-32"
              >
                <div className="h-3 w-3/4 bg-secondary animate-pulse rounded mb-2" />
                <div className="h-2 w-1/2 bg-secondary animate-pulse rounded mb-3" />
                <div className="h-6 w-full bg-secondary animate-pulse rounded" />
              </div>
            ))
          ) : pendingProposals.length === 0 ? (
            <div className="flex flex-col items-center justify-center flex-1 py-8">
              <FileCheck className="w-6 h-6 text-muted-foreground/40 mb-2" />
              <p className="text-xs text-muted-foreground text-center">
                No pending proposals
              </p>
            </div>
          ) : (
            pendingProposals.map((p) => <ProposalCard key={p.id} proposal={p} />)
          )
        ) : isLoading ? (
          Array.from({ length: 1 }).map((_, i) => (
            <div
              key={i}
              className="bg-card rounded border border-border p-3 h-24"
            >
              <div className="h-3 w-3/4 bg-secondary animate-pulse rounded mb-2" />
              <div className="h-2 w-1/2 bg-secondary animate-pulse rounded mb-3" />
              <div className="h-2 w-full bg-secondary animate-pulse rounded" />
            </div>
          ))
        ) : runningSims.length === 0 ? (
          <div className="flex flex-col items-center justify-center flex-1 py-8">
            <FlaskConical className="w-6 h-6 text-muted-foreground/40 mb-2" />
            <p className="text-xs text-muted-foreground text-center">
              No running simulations
            </p>
          </div>
        ) : (
          runningSims.map((s) => <SimulationCard key={s.id} simulation={s} />)
        )}
      </div>
    </div>
  );
}