"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
  if (score < 0.5) return "var(--color-red-400)";
  if (score < 0.7) return "var(--amber-alert)";
  return "var(--emerald-data)";
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
    <motion.div
      className="rounded-lg p-3 relative overflow-hidden"
      style={{
        background: "rgba(15, 22, 41, 0.7)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(34, 211, 238, 0.1)",
        boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.04), 0 4px 12px rgba(0, 0, 0, 0.3)",
      }}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{
        y: -2,
        borderColor: "rgba(34, 211, 238, 0.2)",
        boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.08), 0 8px 16px rgba(0, 0, 0, 0.4)",
      }}
    >
      {/* Animated scan line */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        initial={{ opacity: 0 }}
        whileHover={{ opacity: 1 }}
      >
        <motion.div
          className="absolute inset-0"
          style={{
            background: "linear-gradient(180deg, transparent 0%, rgba(34, 211, 238, 0.03) 50%, transparent 100%)",
            backgroundSize: "100% 200%",
          }}
          animate={{
            backgroundPosition: ["0% 0%", "0% 200%"],
          }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        />
      </motion.div>

      <div className="flex items-start justify-between mb-2 relative z-10">
        <h4 className="text-sm font-medium text-foreground leading-tight flex-1 min-w-0 pr-2">
          {proposal.title}
        </h4>
        <motion.span
          className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ml-2 font-medium ${riskColor(proposal.risk_level)}`}
          whileHover={{ scale: 1.05 }}
        >
          {proposal.risk_level.toUpperCase()}
        </motion.span>
      </div>

      <div className="flex items-center gap-2 mb-3 relative z-10">
        <span className="text-[10px] text-muted-foreground">Confidence</span>
        <div className="flex-1 h-1.5 rounded-full overflow-hidden relative">
          <div
            className="absolute inset-0"
            style={{
              background: "rgba(34, 211, 238, 0.08)",
            }}
          />
          <motion.div
            className="h-full rounded-full relative"
            style={{
              width: `${Math.round(proposal.confidence_score * 100)}%`,
              backgroundColor: confidenceColor(proposal.confidence_score),
              boxShadow: `0 0 12px ${confidenceColor(proposal.confidence_score)}`,
            }}
            initial={{ width: 0 }}
            animate={{ width: `${Math.round(proposal.confidence_score * 100)}%` }}
            transition={{ duration: 0.8, delay: 0.2 }}
          />
        </div>
        <span
          className={`text-[10px] font-medium ${confidenceTextColor(proposal.confidence_score)}`}
          style={{
            fontFamily: "var(--font-plex-mono), monospace",
            textShadow: "0 0 8px currentColor",
          }}
        >
          {Math.round(proposal.confidence_score * 100)}%
        </span>
      </div>

      <div className="flex gap-2 relative z-10">
        <motion.button
          className="flex-1 py-1.5 text-xs font-medium rounded border transition-colors"
          style={{
            background: "rgba(16, 185, 129, 0.1)",
            borderColor: "rgba(16, 185, 129, 0.25)",
            color: "#10B981",
          }}
          whileHover={{
            background: "rgba(16, 185, 129, 0.2)",
            borderColor: "rgba(16, 185, 129, 0.4)",
            boxShadow: "0 0 16px rgba(16, 185, 129, 0.2)",
          }}
          whileTap={{ scale: 0.98 }}
          onClick={() =>
            approveMutation.mutate({ id: proposal.id, reviewer: "human" })
          }
        >
          Approve
        </motion.button>
        <motion.button
          className="flex-1 py-1.5 text-xs font-medium rounded border transition-colors"
          style={{
            background: "rgba(239, 68, 68, 0.1)",
            borderColor: "rgba(239, 68, 68, 0.25)",
            color: "#EF4444",
          }}
          whileHover={{
            background: "rgba(239, 68, 68, 0.2)",
            borderColor: "rgba(239, 68, 68, 0.4)",
            boxShadow: "0 0 16px rgba(239, 68, 68, 0.2)",
          }}
          whileTap={{ scale: 0.98 }}
          onClick={() =>
            rejectMutation.mutate({ id: proposal.id, reviewer: "human" })
          }
        >
          Reject
        </motion.button>
      </div>
    </motion.div>
  );
}

function SimulationCard({ simulation }: { simulation: SimulationRun }) {
  const elapsed = simulation.started_at
    ? Math.floor(
        (Date.now() - new Date(simulation.started_at).getTime()) / 1000
      )
    : 0;
  const remaining = Math.max(0, simulation.timeout_seconds - elapsed);
  const progress = Math.min(100, (elapsed / simulation.timeout_seconds) * 100);

  return (
    <motion.div
      className="rounded-lg p-3 relative overflow-hidden"
      style={{
        background: "rgba(15, 22, 41, 0.7)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(34, 211, 238, 0.12)",
        boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.04), 0 4px 12px rgba(0, 0, 0, 0.3)",
      }}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Animated cyan border scan */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{
          border: "1px solid rgba(34, 211, 238, 0.08)",
          borderRadius: "inherit",
        }}
        animate={{
          borderColor: ["rgba(34, 211, 238, 0.08)", "rgba(34, 211, 238, 0.2)", "rgba(34, 211, 238, 0.08)"],
        }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="flex items-start justify-between mb-2 relative z-10">
        <h4 className="text-sm font-medium text-foreground leading-tight flex-1 min-w-0 pr-2">
          {simulation.scenario.name}
        </h4>
        <motion.span
          className="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0 ml-2"
          style={{
            background: "rgba(34, 211, 238, 0.12)",
            color: "#22D3EE",
            border: "1px solid rgba(34, 211, 238, 0.25)",
            boxShadow: "0 0 12px rgba(34, 211, 238, 0.15)",
          }}
          animate={{
            boxShadow: ["0 0 12px rgba(34, 211, 238, 0.15)", "0 0 20px rgba(34, 211, 238, 0.25)", "0 0 12px rgba(34, 211, 238, 0.15)"],
          }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          RUNNING
        </motion.span>
      </div>

      <div className="mb-2 relative z-10">
        <div className="h-1.5 rounded-full overflow-hidden relative">
          <div
            className="absolute inset-0"
            style={{
              background: "rgba(34, 211, 238, 0.08)",
            }}
          />
          <motion.div
            className="h-full rounded-full relative"
            style={{
              width: `${progress}%`,
              background: "linear-gradient(90deg, #22D3EE 0%, #67E8F9 100%)",
              boxShadow: "0 0 12px rgba(34, 211, 238, 0.4)",
            }}
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      <span className="text-[10px] text-muted-foreground font-[family-name:var(--font-plex-mono)] relative z-10">
        ETA: <span className="text-inkos-cyan">{remaining}s</span> · Timeout: {simulation.timeout_seconds}s
      </span>
    </motion.div>
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
      {/* Tab Switcher - Holographic Style */}
      <div
        className="flex gap-1 mb-3 shrink-0 rounded-lg p-1 relative"
        style={{
          background: "rgba(15, 22, 41, 0.6)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(34, 211, 238, 0.1)",
        }}
      >
        <AnimatePresence>
          {/* Active tab background */}
          <motion.div
            className="absolute top-1 bottom-1 w-[calc(50%-4px)]"
            style={{
              left: tab === "pending" ? "4px" : "50%",
            }}
            initial={false}
            animate={{
              left: tab === "pending" ? "4px" : "50%",
            }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          >
            <div
              className="absolute inset-0 rounded"
              style={{
                background: "rgba(21, 28, 48, 0.9)",
                border: "1px solid rgba(34, 211, 238, 0.12)",
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.3)",
              }}
            />
          </motion.div>
        </AnimatePresence>

        <motion.button
          className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors relative z-10 ${
            tab === "pending" ? "text-foreground" : "text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setTab("pending")}
          whileTap={{ scale: 0.98 }}
        >
          Pending ({pendingProposals.length})
        </motion.button>
        <motion.button
          className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors relative z-10 ${
            tab === "running" ? "text-foreground" : "text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setTab("running")}
          whileTap={{ scale: 0.98 }}
        >
          Running ({runningSims.length})
        </motion.button>
      </div>

      {/* Content Area */}
      <div className="flex-1 flex flex-col gap-3 overflow-y-auto">
        <AnimatePresence mode="wait">
          {tab === "pending" ? (
            isLoading ? (
              Array.from({ length: 2 }).map((_, i) => (
                <motion.div
                  key={i}
                  className="rounded-lg p-3 h-32"
                  style={{
                    background: "rgba(15, 22, 41, 0.5)",
                    border: "1px solid rgba(34, 211, 238, 0.08)",
                  }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <div className="h-3 w-3/4 bg-secondary animate-pulse rounded mb-2" />
                  <div className="h-2 w-1/2 bg-secondary animate-pulse rounded mb-3" />
                  <div className="h-6 w-full bg-secondary animate-pulse rounded" />
                </motion.div>
              ))
            ) : pendingProposals.length === 0 ? (
              <motion.div
                key="empty-pending"
                className="flex flex-col items-center justify-center flex-1 py-8"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
              >
                <FileCheck className="w-6 h-6 text-muted-foreground/40 mb-2" />
                <p className="text-xs text-muted-foreground text-center">
                  No pending proposals
                </p>
              </motion.div>
            ) : (
              pendingProposals.map((p) => (
                <ProposalCard key={p.id} proposal={p} />
              ))
            )
          ) : isLoading ? (
            Array.from({ length: 1 }).map((_, i) => (
              <motion.div
                key={i}
                className="rounded-lg p-3 h-24"
                style={{
                  background: "rgba(15, 22, 41, 0.5)",
                  border: "1px solid rgba(34, 211, 238, 0.08)",
                }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <div className="h-3 w-3/4 bg-secondary animate-pulse rounded mb-2" />
                <div className="h-2 w-1/2 bg-secondary animate-pulse rounded mb-3" />
                <div className="h-2 w-full bg-secondary animate-pulse rounded" />
              </motion.div>
            ))
          ) : runningSims.length === 0 ? (
            <motion.div
              key="empty-running"
              className="flex flex-col items-center justify-center flex-1 py-8"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <FlaskConical className="w-6 h-6 text-muted-foreground/40 mb-2" />
              <p className="text-xs text-muted-foreground text-center">
                No running simulations
              </p>
            </motion.div>
          ) : (
            runningSims.map((s) => <SimulationCard key={s.id} simulation={s} />)
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
