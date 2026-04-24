"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Vote,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SkeletonCard, EmptyState } from "@/components/skeleton";
import {
  useProposals,
  useApproveProposal,
  useRejectProposal,
} from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import type { Proposal, ProposalStatus, RiskLevel } from "@/types";

const STATUS_CONFIG: Record<
  ProposalStatus,
  { icon: React.ElementType; colour: string; label: string }
> = {
  pending_approval: {
    icon: Clock,
    colour: "border-amber-400/25 text-amber-400",
    label: "Pending",
  },
  approved: {
    icon: CheckCircle2,
    colour: "border-emerald-500/25 text-emerald-400",
    label: "Approved",
  },
  rejected: {
    icon: XCircle,
    colour: "border-red-400/25 text-red-400",
    label: "Rejected",
  },
  implemented: {
    icon: ShieldCheck,
    colour: "border-inkos-cyan/25 text-inkos-cyan",
    label: "Implemented",
  },
};

const RISK_COLOURS: Record<RiskLevel, string> = {
  low: "border-emerald-500/20 text-emerald-400",
  medium: "border-amber-400/20 text-amber-400",
  high: "border-red-400/20 text-red-400",
};

export default function ProposalsPage() {
  const [statusFilter, setStatusFilter] = useState<ProposalStatus | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [actingId, setActingId] = useState<string | null>(null);

  const { data: proposals, isLoading } = useProposals(
    statusFilter === "all" ? undefined : statusFilter,
  );
  const approveMutation = useApproveProposal();
  const rejectMutation = useRejectProposal();

  async function handleApprove(id: string) {
    setActingId(id);
    try {
      await approveMutation.mutateAsync({ id, reviewer: "web-user" });
    } finally {
      setActingId(null);
    }
  }

  async function handleReject(id: string) {
    setActingId(id);
    try {
      await rejectMutation.mutateAsync({
        id,
        reviewer: "web-user",
        reason: "Rejected via web console",
      });
    } finally {
      setActingId(null);
    }
  }

  const counts = {
    all: proposals?.length ?? 0,
    pending_approval:
      proposals?.filter((p) => p.status === "pending_approval").length ?? 0,
    approved: proposals?.filter((p) => p.status === "approved").length ?? 0,
    rejected: proposals?.filter((p) => p.status === "rejected").length ?? 0,
    implemented:
      proposals?.filter((p) => p.status === "implemented").length ?? 0,
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6 page-transition">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="flex items-center gap-3"
      >
        <div className="h-9 w-9 rounded-lg bg-amber-400/[0.06] border border-amber-400/15 flex items-center justify-center">
          <Vote className="h-5 w-5 text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            <span className="text-amber-400">Proposals</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Self-modification governance — review, approve, or reject
          </p>
        </div>
      </motion.div>

      {/* Status filter tabs */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="flex items-center gap-2 flex-wrap"
      >
        {(
          ["all", "pending_approval", "approved", "rejected", "implemented"] as const
        ).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "text-xs px-3 py-1.5 rounded-full border transition-all duration-200",
              statusFilter === s
                ? "bg-inkos-cyan/10 border-inkos-cyan/25 text-inkos-cyan"
                : "border-white/[0.06] text-muted-foreground hover:border-inkos-cyan/15",
            )}
          >
            {s === "all" ? "All" : STATUS_CONFIG[s].label} ({counts[s]})
          </button>
        ))}
      </motion.div>

      {/* Proposals list */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="space-y-3"
      >
        {isLoading ? (
          <div className="space-y-3">
            <SkeletonCard lines={4} />
            <SkeletonCard lines={3} />
            <SkeletonCard lines={4} />
          </div>
        ) : !proposals || proposals.length === 0 ? (
          <Card className="glass border-inkos-cyan/8">
            <CardContent>
              <EmptyState
                icon={Vote}
                title="No proposals yet"
                description="Prime will automatically generate proposals from system introspection. They'll appear here for your review."
              />
            </CardContent>
          </Card>
        ) : (
          proposals.map((proposal) => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              expanded={expanded === proposal.id}
              onToggle={() =>
                setExpanded(expanded === proposal.id ? null : proposal.id)
              }
              onApprove={() => handleApprove(proposal.id)}
              onReject={() => handleReject(proposal.id)}
              isActing={actingId === proposal.id}
            />
          ))
        )}
      </motion.div>
    </div>
  );
}

function ProposalCard({
  proposal,
  expanded,
  onToggle,
  onApprove,
  onReject,
  isActing,
}: {
  proposal: Proposal;
  expanded: boolean;
  onToggle: () => void;
  onApprove: () => void;
  onReject: () => void;
  isActing: boolean;
}) {
  const config = STATUS_CONFIG[proposal.status];
  const StatusIcon = isActing ? Loader2 : config.icon;

  return (
    <Card className="glass glass-hover border-inkos-cyan/8 overflow-hidden">
      {/* Main row */}
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-inkos-cyan/[0.02] transition-colors duration-150"
      >
        <StatusIcon
          className={cn(
            "h-5 w-5 shrink-0",
            isActing ? "animate-spin text-inkos-cyan" : config.colour.split(" ")[1],
          )}
        />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{proposal.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            by {proposal.proposed_by} ·{" "}
            {formatDistanceToNow(new Date(proposal.created_at), {
              addSuffix: true,
            })}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge
            variant="outline"
            className={cn("text-[10px] font-mono", RISK_COLOURS[proposal.risk_level])}
          >
            {proposal.risk_level}
          </Badge>
          <Badge variant="outline" className={cn("text-[10px]", config.colour)}>
            {config.label}
          </Badge>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expanded details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Separator className="bg-white/[0.04]" />
            <div className="px-5 py-4 space-y-3 text-sm">
              <DetailRow
                label="Modification Type"
                value={proposal.modification_type.replace(/_/g, " ")}
              />
              <DetailRow label="Description" value={proposal.description} />
              <DetailRow label="Reasoning" value={proposal.reasoning} />
              <DetailRow label="Expected Impact" value={proposal.expected_impact} />

              <div className="flex items-center gap-3">
                <DetailRow
                  label="Confidence"
                  value={`${Math.round(proposal.confidence_score * 100)}%`}
                />
                {/* Confidence bar */}
                <div className="flex-1 h-1.5 rounded-full bg-white/[0.04] overflow-hidden max-w-[120px]">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      proposal.confidence_score >= 0.7
                        ? "bg-emerald-400"
                        : proposal.confidence_score >= 0.4
                          ? "bg-amber-400"
                          : "bg-red-400",
                    )}
                    style={{
                      width: `${Math.round(proposal.confidence_score * 100)}%`,
                    }}
                  />
                </div>
              </div>

              {proposal.implementation_steps.length > 0 && (
                <div>
                  <span className="text-[11px] text-muted-foreground uppercase tracking-widest">
                    Implementation Steps
                  </span>
                  <ol className="mt-1 ml-4 space-y-1 list-decimal text-xs text-muted-foreground">
                    {proposal.implementation_steps.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Action buttons */}
              {proposal.status === "pending_approval" && (
                <div className="flex items-center gap-2 pt-2">
                  <Button
                    size="sm"
                    className="bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/25 border border-emerald-500/20"
                    onClick={(e) => {
                      e.stopPropagation();
                      onApprove();
                    }}
                    disabled={isActing}
                  >
                    {isActing ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
                    )}
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onReject();
                    }}
                    disabled={isActing}
                  >
                    {isActing ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 mr-1.5" />
                    )}
                    Reject
                  </Button>
                </div>
              )}

              {proposal.confidence_score < 0.5 && (
                <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-400/[0.04] rounded-md px-3 py-2 border border-amber-400/12">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  Low confidence score — proceed with caution
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-[11px] text-muted-foreground uppercase tracking-widest">
        {label}
      </span>
      <p className="mt-0.5 text-muted-foreground leading-relaxed">{value}</p>
    </div>
  );
}
