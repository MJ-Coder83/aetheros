"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lightbulb,
  Search,
  ChevronRight,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  ArrowRight,
  Info,
  BarChart3,
  Clock,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useExplanations,
  useGenerateExplanation,
  useDecisionTrace,
  useKeyFactors,
} from "@/hooks/use-api";
import type { ActionType, Explanation, KeyFactor, DecisionTrace } from "@/types";

/* ── Action type options ────────────────────────────────────── */

const ACTION_TYPES: { value: ActionType; label: string }[] = [
  { value: "proposal_created", label: "Proposal Created" },
  { value: "proposal_approved", label: "Proposal Approved" },
  { value: "skill_evolution", label: "Skill Evolution" },
  { value: "simulation_run", label: "Simulation Run" },
  { value: "debate_concluded", label: "Debate Concluded" },
  { value: "system_action", label: "System Action" },
];

/* ── Confidence gauge ───────────────────────────────────────── */

function ConfidenceGauge({ value, size = 120 }: { value: number; size?: number }) {
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = circumference * (1 - value);
  const color =
    value >= 0.8
      ? "text-emerald-400"
      : value >= 0.6
        ? "text-inkos-cyan"
        : value >= 0.4
          ? "text-amber-400"
          : "text-red-400";

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={6}
          className="text-inkos-navy-800/60"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={6}
          strokeDasharray={circumference}
          strokeDashoffset={progress}
          strokeLinecap="round"
          className={cn(color, "transition-all duration-700")}
        />
      </svg>
      <span className={cn("absolute text-2xl font-bold tabular-nums", color)}>
        {Math.round(value * 100)}%
      </span>
    </div>
  );
}

/* ── Factor importance bar ──────────────────────────────────── */

function FactorBar({ factor }: { factor: KeyFactor }) {
  const dirColor =
    factor.direction === "supporting"
      ? "bg-emerald-500/70"
      : factor.direction === "opposing"
        ? "bg-red-500/70"
        : "bg-inkos-purple/50";

  const dirBadge =
    factor.direction === "supporting"
      ? "text-emerald-400 border-emerald-400/30"
      : factor.direction === "opposing"
        ? "text-red-400 border-red-400/30"
        : "text-muted-foreground border-inkos-purple/30";

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium truncate">{factor.name}</span>
          <span
            className={cn(
              "text-[10px] font-medium uppercase px-1.5 py-0.5 rounded border",
              dirBadge,
            )}
          >
            {factor.direction}
          </span>
        </div>
        <span className="text-xs tabular-nums text-muted-foreground">
          {(factor.importance * 100).toFixed(0)}%
        </span>
      </div>
      <div className="h-2 rounded-full bg-inkos-navy-800/60 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${factor.importance * 100}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className={cn("h-full rounded-full", dirColor)}
        />
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">
        {factor.description}
      </p>
      {factor.evidence.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {factor.evidence.map((e, i) => (
            <span
              key={i}
              className="text-[10px] px-1.5 py-0.5 rounded bg-inkos-navy-800/40 text-muted-foreground border border-inkos-purple/10"
            >
              {e}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Decision timeline ──────────────────────────────────────── */

function DecisionTimeline({ trace }: { trace: DecisionTrace }) {
  return (
    <div className="relative pl-6">
      {/* Vertical line */}
      <div className="absolute left-2.5 top-1 bottom-1 w-px bg-inkos-purple/20" />

      {trace.steps.map((step, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.08 }}
          className="relative pb-6 last:pb-0"
        >
          {/* Dot */}
          <div
            className={cn(
              "absolute left-[-14px] top-1 h-3 w-3 rounded-full border-2",
              step.confidence >= 0.8
                ? "bg-emerald-500/50 border-emerald-400"
                : step.confidence >= 0.5
                  ? "bg-inkos-cyan/50 border-inkos-cyan"
                  : "bg-amber-500/50 border-amber-400",
            )}
          />

          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-xs font-mono text-muted-foreground">
                Step {step.step_number}
              </span>
              <span className="text-xs tabular-nums px-1.5 py-0.5 rounded bg-inkos-navy-800/40 text-muted-foreground">
                {(step.confidence * 100).toFixed(0)}% conf
              </span>
            </div>
            <p className="text-sm font-medium">{step.action}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {step.rationale}
            </p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

/* ── Risk badge ─────────────────────────────────────────────── */

function RiskBadge({ level }: { level: string }) {
  const style =
    level === "high"
      ? "bg-red-500/20 text-red-400 border-red-400/30"
      : level === "medium"
        ? "bg-amber-500/20 text-amber-400 border-amber-400/30"
        : "bg-emerald-500/20 text-emerald-400 border-emerald-400/30";

  return (
    <span className={cn("text-xs font-medium px-2 py-1 rounded border", style)}>
      {level} risk
    </span>
  );
}

/* ── Explanation detail card ─────────────────────────────────── */

function ExplanationDetail({ explanation }: { explanation: Explanation }) {
  const [activeTab, setActiveTab] = useState<"factors" | "trace" | "summary">(
    "factors",
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-xl border border-inkos-purple/20 overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-inkos-purple/10 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Lightbulb className="h-4 w-4 text-inkos-cyan" />
            <span className="text-sm font-mono text-muted-foreground truncate">
              {explanation.action_id}
            </span>
            <RiskBadge level={explanation.risk_level} />
          </div>
          <p className="text-xs text-muted-foreground">
            {explanation.action_type.replace(/_/g, " ")} &middot;{" "}
            {new Date(explanation.created_at).toLocaleString()}
          </p>
        </div>
        <ConfidenceGauge value={explanation.confidence} size={80} />
      </div>

      {/* Simplified summary */}
      <div className="px-6 py-3 bg-inkos-navy-800/20 border-b border-inkos-purple/10">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-inkos-cyan mt-0.5 shrink-0" />
          <p className="text-sm leading-relaxed">{explanation.simplified_summary}</p>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="px-6 pt-3 flex gap-1 border-b border-inkos-purple/10">
        {(
          [
            { key: "factors", label: "Key Factors", icon: BarChart3 },
            { key: "trace", label: "Decision Trace", icon: Clock },
            { key: "summary", label: "Technical", icon: Layers },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-t-md transition-all",
              activeTab === tab.key
                ? "bg-inkos-purple/15 text-inkos-cyan border-b-2 border-inkos-cyan"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="px-6 py-4">
        <AnimatePresence mode="wait">
          {activeTab === "factors" && (
            <motion.div
              key="factors"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {explanation.key_factors.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No key factors identified for this action.
                </p>
              ) : (
                explanation.key_factors.map((f, i) => (
                  <FactorBar key={i} factor={f} />
                ))
              )}
            </motion.div>
          )}

          {activeTab === "trace" && explanation.decision_trace && (
            <motion.div
              key="trace"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <DecisionTimeline trace={explanation.decision_trace} />

              {/* Assumptions */}
              {explanation.decision_trace.assumptions.length > 0 && (
                <div className="mt-4 pt-3 border-t border-inkos-purple/10">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                    Assumptions
                  </h4>
                  <ul className="space-y-1">
                    {explanation.decision_trace.assumptions.map((a, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex gap-1.5">
                        <span className="text-inkos-purple">&#8226;</span>
                        {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Limitations */}
              {explanation.decision_trace.limitations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-inkos-purple/10">
                  <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                    Limitations
                  </h4>
                  <ul className="space-y-1">
                    {explanation.decision_trace.limitations.map((l, i) => (
                      <li
                        key={i}
                        className="text-xs text-amber-400/80 flex gap-1.5"
                      >
                        <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                        {l}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === "trace" && !explanation.decision_trace && (
            <p className="text-sm text-muted-foreground">
              No decision trace available for this explanation.
            </p>
          )}

          {activeTab === "summary" && (
            <motion.div
              key="summary"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <p className="text-sm text-muted-foreground leading-relaxed font-mono">
                {explanation.technical_summary}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

/* ── Main page ──────────────────────────────────────────────── */

export default function ExplainPage() {
  const [actionId, setActionId] = useState("");
  const [actionType, setActionType] = useState<ActionType>("proposal_created");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: explanations = [], isLoading } = useExplanations();
  const generateMutation = useGenerateExplanation();
  const traceMutation = useDecisionTrace();
  const factorsMutation = useKeyFactors();

  const handleGenerate = () => {
    if (!actionId.trim()) return;
    generateMutation.mutate({
      action_id: actionId.trim(),
      action_type: actionType,
    });
  };

  const selectedExplanation = explanations.find(
    (e) => e.id === expandedId,
  );

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Lightbulb className="h-8 w-8 text-inkos-cyan text-glow-cyan" />
          <span>
            <span className="text-inkos-purple text-glow-purple">Explain</span>ability
          </span>
        </h1>
        <p className="text-muted-foreground mt-1">
          Understand why Prime made specific decisions. Full transparency into
          reasoning, factors, and confidence.
        </p>
      </div>

      {/* Generate explanation form */}
      <div className="glass rounded-xl border border-inkos-purple/20 p-5 space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Generate Explanation
        </h2>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={actionId}
            onChange={(e) => setActionId(e.target.value)}
            placeholder="Enter action ID (e.g. proposal-abc123)"
            className="flex-1 rounded-md border border-inkos-purple/20 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan"
            onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
          />
          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value as ActionType)}
            className="rounded-md border border-inkos-purple/20 bg-inkos-navy-800/30 px-3 py-2 text-sm focus:border-inkos-cyan focus:outline-none"
          >
            {ACTION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <button
            onClick={handleGenerate}
            disabled={!actionId.trim() || generateMutation.isPending}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              actionId.trim() && !generateMutation.isPending
                ? "bg-inkos-purple text-white hover:bg-inkos-purple/80"
                : "bg-inkos-navy-800/40 text-muted-foreground cursor-not-allowed",
            )}
          >
            {generateMutation.isPending ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                >
                  <Search className="h-4 w-4" />
                </motion.div>
                Analysing...
              </>
            ) : (
              <>
                <Lightbulb className="h-4 w-4" />
                Explain
              </>
            )}
          </button>
        </div>

        {/* Quick actions */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => {
              if (!actionId.trim()) return;
              traceMutation.mutate({
                action_id: actionId.trim(),
                action_type: actionType,
              });
            }}
            disabled={!actionId.trim() || traceMutation.isPending}
            className="text-xs px-3 py-1.5 rounded border border-inkos-cyan/20 text-inkos-cyan hover:bg-inkos-cyan/10 transition-all disabled:opacity-50"
          >
            <Clock className="h-3 w-3 inline mr-1" />
            Trace Decision
          </button>
          <button
            onClick={() => {
              if (!actionId.trim()) return;
              factorsMutation.mutate({
                action_id: actionId.trim(),
                action_type: actionType,
              });
            }}
            disabled={!actionId.trim() || factorsMutation.isPending}
            className="text-xs px-3 py-1.5 rounded border border-inkos-purple/20 text-inkos-purple hover:bg-inkos-purple/10 transition-all disabled:opacity-50"
          >
            <BarChart3 className="h-3 w-3 inline mr-1" />
            Key Factors
          </button>
        </div>
      </div>

      {/* Mutation result displays */}
      {traceMutation.data && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-xl border border-inkos-cyan/20 p-5"
        >
          <h3 className="text-sm font-medium text-inkos-cyan mb-3 flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Decision Trace
          </h3>
          <DecisionTimeline trace={traceMutation.data as unknown as DecisionTrace} />
        </motion.div>
      )}

      {factorsMutation.data && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-xl border border-inkos-purple/20 p-5 space-y-3"
        >
          <h3 className="text-sm font-medium text-inkos-purple mb-2 flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Key Factors
          </h3>
          {(factorsMutation.data as unknown as KeyFactor[]).map((f, i) => (
            <FactorBar key={i} factor={f} />
          ))}
        </motion.div>
      )}

      {/* Explanations list */}
      <div>
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-inkos-purple" />
          Past Explanations
        </h2>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-20 rounded-xl bg-inkos-navy-800/30 animate-pulse border border-inkos-purple/10"
              />
            ))}
          </div>
        ) : explanations.length === 0 ? (
          <div className="glass rounded-xl border border-inkos-purple/10 p-12 text-center">
            <Lightbulb className="h-10 w-10 mx-auto text-muted-foreground/30 mb-3" />
            <p className="text-muted-foreground text-sm">
              No explanations yet. Generate one above to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {explanations.map((exp) => (
              <motion.button
                key={exp.id}
                onClick={() =>
                  setExpandedId(
                    expandedId === exp.id ? null : exp.id,
                  )
                }
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full text-left glass rounded-xl border border-inkos-purple/20 p-4 hover:border-inkos-purple/40 transition-all"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono">{exp.action_id}</span>
                      <RiskBadge level={exp.risk_level} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {exp.action_type.replace(/_/g, " ")} &middot;{" "}
                      {new Date(exp.created_at).toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                      {exp.simplified_summary}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <ConfidenceGauge value={exp.confidence} size={48} />
                    <ChevronRight
                      className={cn(
                        "h-4 w-4 text-muted-foreground transition-transform",
                        expandedId === exp.id && "rotate-90",
                      )}
                    />
                  </div>
                </div>

                {/* Expanded detail */}
                <AnimatePresence>
                  {expandedId === exp.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-4 pt-4 border-t border-inkos-purple/10">
                        <ExplanationDetail explanation={exp} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
