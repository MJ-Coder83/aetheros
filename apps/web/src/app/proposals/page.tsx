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
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useProposals, useApproveProposal, useRejectProposal } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import type { Proposal, ProposalStatus, RiskLevel } from "@/types";

const STATUS_CONFIG: Record<ProposalStatus, { icon: React.ElementType; colour: string; label: string }> = {
  pending_approval: { icon: Clock, colour: "border-amber-400/40 text-amber-400", label: "Pending" },
  approved: { icon: CheckCircle2, colour: "border-emerald-400/40 text-emerald-400", label: "Approved" },
  rejected: { icon: XCircle, colour: "border-red-400/40 text-red-400", label: "Rejected" },
  implemented: { icon: ShieldCheck, colour: "border-inkos-cyan/40 text-inkos-cyan-400", label: "Implemented" },
};

const RISK_COLOURS: Record<RiskLevel, string> = {
  low: "border-emerald-400/30 text-emerald-400",
  medium: "border-amber-400/30 text-amber-400",
  high: "border-red-400/30 text-red-400",
};

export default function ProposalsPage() {
  const [statusFilter, setStatusFilter] = useState<ProposalStatus | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const { data: proposals, isLoading } = useProposals(
    statusFilter === "all" ? undefined : statusFilter,
  );
  const approveMutation = useApproveProposal();
  const rejectMutation = useRejectProposal();

  const counts = {
    all: proposals?.length ?? 0,
    pending_approval: proposals?.filter((p) => p.status === "pending_approval").length ?? 0,
    approved: proposals?.filter((p) => p.status === "approved").length ?? 0,
    rejected: proposals?.filter((p) => p.status === "rejected").length ?? 0,
    implemented: proposals?.filter((p) => p.status === "implemented").length ?? 0,
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3"
      >
        <Vote className="h-7 w-7 text-amber-400" />
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
        transition={{ delay: 0.05 }}
        className="flex items-center gap-2 flex-wrap"
      >
        {(["all", "pending_approval", "approved", "rejected", "implemented"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "text-xs px-3 py-1.5 rounded-full border transition-all",
              statusFilter === s
                ? "bg-inkos-purple/20 border-inkos-purple/40 text-inkos-purple-400"
                : "border-border text-muted-foreground hover:border-inkos-purple/30",
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
        transition={{ delay: 0.1 }}
        className="space-y-3"
      >
        {isLoading ? (
          <div className="space-y-3 animate-pulse">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 rounded-xl bg-muted/30" />
            ))}
          </div>
        ) : !proposals || proposals.length === 0 ? (
          <Card className="glass border-inkos-purple/20">
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              No proposals found. Prime will generate them from introspection.
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
              onApprove={() =>
                approveMutation.mutate({ id: proposal.id, reviewer: "web-user" })
              }
              onReject={() =>
                rejectMutation.mutate({
                  id: proposal.id,
                  reviewer: "web-user",
                  reason: "Rejected via web console",
                })
              }
              isApproving={approveMutation.isPending}
              isRejecting={rejectMutation.isPending}
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
  isApproving,
  isRejecting,
}: {
  proposal: Proposal;
  expanded: boolean;
  onToggle: () => void;
  onApprove: () => void;
  onReject: () => void;
  isApproving: boolean;
  isRejecting: boolean;
}) {
  const config = STATUS_CONFIG[proposal.status];
  const StatusIcon = config.icon;

  return (
    <Card className="glass border-inkos-purple/20 overflow-hidden">
      {/* Main row */}
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-inkos-purple/5 transition-colors"
      >
        <StatusIcon className={cn("h-5 w-5 shrink-0", config.colour.split(" ")[1])} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{proposal.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            by {proposal.proposed_by} ·{" "}
            {formatDistanceToNow(new Date(proposal.created_at), { addSuffix: true })}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="outline" className={cn("text-[10px] font-mono", RISK_COLOURS[proposal.risk_level])}>
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
            <Separator className="bg-inkos-purple/15" />
            <div className="px-5 py-4 space-y-3 text-sm">
              <DetailRow label="Modification Type" value={proposal.modification_type.replace(/_/g, " ")} />
              <DetailRow label="Description" value={proposal.description} />
              <DetailRow label="Reasoning" value={proposal.reasoning} />
              <DetailRow label="Expected Impact" value={proposal.expected_impact} />
              <DetailRow label="Confidence" value={`${Math.round(proposal.confidence_score * 100)}%`} />

              {proposal.implementation_steps.length > 0 && (
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">
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
                    className="bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={(e) => {
                      e.stopPropagation();
                      onApprove();
                    }}
                    disabled={isApproving || isRejecting}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onReject();
                    }}
                    disabled={isApproving || isRejecting}
                  >
                    <XCircle className="h-3.5 w-3.5 mr-1.5" />
                    Reject
                  </Button>
                </div>
              )}

              {proposal.confidence_score < 0.5 && (
                <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-400/5 rounded-md px-3 py-2 border border-amber-400/20">
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
      <span className="text-xs text-muted-foreground uppercase tracking-wider">
        {label}
      </span>
      <p className="mt-0.5 text-muted-foreground">{value}</p>
    </div>
  );
}
