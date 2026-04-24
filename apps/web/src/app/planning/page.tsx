"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Route,
  Play,
  Square,
  SkipForward,
  RotateCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Target,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Types ───────────────────────────────────────────────────── */

interface PlanStep {
  step_id: string;
  name: string;
  action: string;
  description: string;
  dependencies: string[];
  status: string;
  retry_count: number;
  max_retries: number;
  result: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
}

interface Plan {
  id: string;
  goal: string;
  description: string;
  steps: PlanStep[];
  status: string;
  failure_policy: string;
  priority: string;
  progress_pct: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

/* ── Status helpers ──────────────────────────────────────────── */

const planStatusColors: Record<string, string> = {
  draft: "bg-amber-500/20 text-amber-400 border-amber-400/30",
  active: "bg-inkos-cyan/20 text-inkos-cyan border-inkos-cyan/30",
  completed: "bg-emerald-500/20 text-emerald-400 border-emerald-400/30",
  failed: "bg-red-500/20 text-red-400 border-red-400/30",
  aborted: "bg-gray-500/20 text-gray-400 border-gray-400/30",
};

const stepStatusIcons: Record<string, React.ReactNode> = {
  pending: <Clock className="h-4 w-4 text-gray-500" />,
  ready: <Zap className="h-4 w-4 text-amber-400" />,
  running: <Loader2 className="h-4 w-4 text-inkos-cyan animate-spin" />,
  completed: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  failed: <AlertCircle className="h-4 w-4 text-red-400" />,
  skipped: <SkipForward className="h-4 w-4 text-gray-400" />,
  retrying: <RotateCw className="h-4 w-4 text-amber-400 animate-spin" />,
};

const stepStatusBg: Record<string, string> = {
  pending: "bg-gray-500/5 border-gray-500/10",
  ready: "bg-amber-500/5 border-amber-500/10",
  running: "bg-inkos-cyan/5 border-inkos-cyan/10",
  completed: "bg-emerald-500/5 border-emerald-500/10",
  failed: "bg-red-500/5 border-red-500/10",
  skipped: "bg-gray-500/5 border-gray-500/10",
  retrying: "bg-amber-500/5 border-amber-500/10",
};

/* ── Step card ───────────────────────────────────────────────── */

function StepCard({ step }: { step: PlanStep }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={cn(
        "rounded-lg border p-3 transition-all",
        stepStatusBg[step.status] ?? "bg-inkos-navy-800/30 border-inkos-purple/10",
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 text-left"
      >
        {stepStatusIcons[step.status] ?? <Clock className="h-4 w-4" />}
        <span className="text-sm font-medium flex-1">{step.name}</span>
        <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-inkos-navy-800/40 text-muted-foreground border border-inkos-purple/10">
          {step.action}
        </span>
        {expanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 pt-2 border-t border-inkos-purple/10 space-y-1.5 text-xs">
              {step.description && (
                <p className="text-muted-foreground">{step.description}</p>
              )}
              {step.dependencies.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">Deps:</span>
                  {step.dependencies.map((dep) => (
                    <span
                      key={dep}
                      className="px-1.5 py-0.5 rounded bg-inkos-navy-800/40 text-muted-foreground border border-inkos-purple/10"
                    >
                      {dep}
                    </span>
                  ))}
                </div>
              )}
              {step.result && (
                <p className="text-emerald-400/80">
                  Result: {step.result}
                </p>
              )}
              {step.error_message && (
                <p className="text-red-400/80">
                  Error: {step.error_message}
                </p>
              )}
              {step.retry_count > 0 && (
                <p className="text-amber-400/60">
                  Retries: {step.retry_count}/{step.max_retries}
                </p>
              )}
              {step.started_at && (
                <p className="text-muted-foreground/50">
                  Started: {new Date(step.started_at).toLocaleTimeString()}
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Plan card ───────────────────────────────────────────────── */

function PlanCard({ plan }: { plan: Plan }) {
  const completedSteps = plan.steps.filter(
    (s) => s.status === "completed" || s.status === "skipped",
  ).length;
  const totalSteps = plan.steps.length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-xl border border-inkos-purple/20 overflow-hidden"
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-inkos-purple/10 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Target className="h-5 w-5 text-inkos-purple shrink-0" />
            <h3 className="text-lg font-semibold truncate">{plan.goal}</h3>
            <span
              className={cn(
                "text-[10px] font-medium uppercase px-1.5 py-0.5 rounded border",
                planStatusColors[plan.status] ??
                  "bg-muted text-muted-foreground",
              )}
            >
              {plan.status}
            </span>
          </div>
          {plan.description && (
            <p className="text-xs text-muted-foreground">{plan.description}</p>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className="text-2xl font-bold text-inkos-cyan">
            {Math.round(plan.progress_pct)}%
          </div>
          <div className="text-[10px] text-muted-foreground">
            {completedSteps}/{totalSteps} steps
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-inkos-navy-800/30">
        <motion.div
          className="h-full bg-gradient-to-r from-inkos-purple to-inkos-cyan"
          initial={{ width: 0 }}
          animate={{ width: `${plan.progress_pct}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>

      {/* Steps list */}
      <div className="p-4 space-y-2">
        {plan.steps.map((step) => (
          <StepCard key={step.step_id} step={step} />
        ))}
      </div>

      {/* Footer info */}
      <div className="px-5 py-2.5 border-t border-inkos-purple/10 flex items-center gap-4 text-[10px] text-muted-foreground bg-inkos-navy-800/20">
        <span>Policy: {plan.failure_policy}</span>
        <span>Priority: {plan.priority}</span>
        <span className="ml-auto">
          {new Date(plan.created_at).toLocaleDateString()}
        </span>
      </div>
    </motion.div>
  );
}

/* ── Main page ───────────────────────────────────────────────── */

const EXAMPLE_GOALS = [
  "Reduce system error rate below 5%",
  "Improve system reliability",
  "Add new skill for data analysis",
  "Create domain for legal research",
  "Evolve skill for better performance",
];

export default function PlanningPage() {
  const [goal, setGoal] = useState("");
  const [plans, setPlans] = useState<Plan[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executingPlanId, setExecutingPlanId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!goal.trim()) return;
    setIsGenerating(true);
    setError(null);

    try {
      const res = await fetch("/api/plans/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: goal.trim() }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      const plan = (await res.json()) as Plan;
      setPlans((prev) => [plan, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExecute = async (planId: string) => {
    setIsExecuting(true);
    setExecutingPlanId(planId);
    setError(null);

    try {
      const res = await fetch(`/api/plans/${planId}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step_timeout: 30.0 }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      // Refresh the plan
      const planRes = await fetch(`/api/plans/${planId}`);
      if (planRes.ok) {
        const updated = (await planRes.json()) as Plan;
        setPlans((prev) =>
          prev.map((p) => (p.id === planId ? updated : p)),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsExecuting(false);
      setExecutingPlanId(null);
    }
  };

  const handleAbort = async (planId: string) => {
    try {
      await fetch(`/api/plans/${planId}/abort`, { method: "POST" });
      const planRes = await fetch(`/api/plans/${planId}`);
      if (planRes.ok) {
        const updated = (await planRes.json()) as Plan;
        setPlans((prev) =>
          prev.map((p) => (p.id === planId ? updated : p)),
        );
      }
    } catch {
      // best-effort
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Route className="h-8 w-8 text-inkos-purple text-glow-purple" />
          <span>
            <span className="text-inkos-purple text-glow-purple">
              Multi-Step
            </span>{" "}
            Planning
          </span>
        </h1>
        <p className="text-muted-foreground mt-1">
          Decompose goals into structured, executable plans with dependency
          tracking and adaptive failure handling.
        </p>
      </div>

      {/* Generation form */}
      <div className="glass rounded-xl border border-inkos-purple/20 p-5 space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Generate Plan from Goal
        </h2>

        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder='e.g. "Reduce system error rate below 5%"'
          rows={2}
          className="w-full rounded-md border border-inkos-purple/20 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan resize-none"
        />

        {/* Example chips */}
        <div className="flex flex-wrap gap-1.5">
          <span className="text-[10px] uppercase text-muted-foreground mr-1 self-center">
            Try:
          </span>
          {EXAMPLE_GOALS.map((ex) => (
            <button
              key={ex}
              onClick={() => setGoal(ex)}
              className="text-[10px] px-2 py-1 rounded border border-inkos-purple/15 text-muted-foreground hover:text-inkos-cyan hover:border-inkos-cyan/30 transition-all truncate max-w-[200px]"
            >
              {ex}
            </button>
          ))}
        </div>

        <button
          onClick={handleGenerate}
          disabled={!goal.trim() || isGenerating}
          className={cn(
            "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
            goal.trim() && !isGenerating
              ? "bg-inkos-purple/80 text-white hover:bg-inkos-purple"
              : "bg-inkos-navy-800/40 text-muted-foreground cursor-not-allowed",
          )}
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate Plan
            </>
          )}
        </button>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-400/30 bg-red-500/10 p-3">
            <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Plans list */}
      {plans.length > 0 && (
        <div className="space-y-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Plans ({plans.length})
          </h2>

          {plans.map((plan) => (
            <div key={plan.id} className="space-y-3">
              <PlanCard plan={plan} />

              {/* Action buttons */}
              <div className="flex gap-2 ml-auto">
                {(plan.status === "draft" || plan.status === "active") && (
                  <button
                    onClick={() => handleExecute(plan.id)}
                    disabled={isExecuting && executingPlanId === plan.id}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                      "bg-inkos-cyan/80 text-inkos-navy-900 hover:bg-inkos-cyan",
                    )}
                  >
                    {isExecuting && executingPlanId === plan.id ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Executing...
                      </>
                    ) : (
                      <>
                        <Play className="h-3.5 w-3.5" />
                        Execute
                      </>
                    )}
                  </button>
                )}
                {plan.status === "active" && (
                  <button
                    onClick={() => handleAbort(plan.id)}
                    className="flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium bg-red-500/20 text-red-400 border border-red-400/20 hover:bg-red-500/30 transition-all"
                  >
                    <Square className="h-3.5 w-3.5" />
                    Abort
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
