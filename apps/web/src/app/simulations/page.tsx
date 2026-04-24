"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FlaskConical,
  Play,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Zap,
  BarChart3,
  Loader2,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { SkeletonCard, EmptyState } from "@/components/skeleton";
import {
  useSimulations,
  useSimulationScenarios,
  useRunSimulation,
  useRollbackSimulation,
  useComparisonReport,
} from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import type {
  SimulationRun,
  SimulationStatus,
  WhatIfScenario,
  OutcomeDelta,
} from "@/types";

const SIM_STATUS_CONFIG: Record<
  SimulationStatus,
  { icon: React.ElementType; colour: string; label: string }
> = {
  pending: {
    icon: Clock,
    colour: "border-amber-400/25 text-amber-400",
    label: "Pending",
  },
  running: {
    icon: Zap,
    colour: "border-inkos-cyan/25 text-inkos-cyan",
    label: "Running",
  },
  completed: {
    icon: CheckCircle2,
    colour: "border-emerald-500/25 text-emerald-400",
    label: "Completed",
  },
  failed: {
    icon: XCircle,
    colour: "border-red-400/25 text-red-400",
    label: "Failed",
  },
  aborted: {
    icon: AlertTriangle,
    colour: "border-amber-400/25 text-amber-400",
    label: "Aborted",
  },
  rolled_back: {
    icon: RotateCcw,
    colour: "border-white/[0.06] text-muted-foreground",
    label: "Rolled Back",
  },
};

const SCENARIO_TYPE_COLOURS: Record<string, string> = {
  skill_evolution: "border-inkos-cyan/25 text-inkos-cyan",
  agent_reconfig: "border-inkos-teal-300/25 text-inkos-teal-300",
  domain_change: "border-emerald-500/25 text-emerald-400",
  custom: "border-amber-400/25 text-amber-400",
};

export default function SimulationsPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showScenarios, setShowScenarios] = useState(false);
  const [compareId, setCompareId] = useState<string | null>(null);

  const { data: simulations, isLoading } = useSimulations();
  const { data: scenarios } = useSimulationScenarios();
  const runMutation = useRunSimulation();
  const rollbackMutation = useRollbackSimulation();
  const { data: comparison } = useComparisonReport(compareId);

  async function handleRun(scenario: WhatIfScenario) {
    await runMutation.mutateAsync({ scenario, timeout: 60 });
    setShowScenarios(false);
  }

  async function handleRollback(id: string) {
    await rollbackMutation.mutateAsync(id);
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6 page-transition">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center">
            <FlaskConical className="h-5 w-5 text-inkos-cyan" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              <span className="text-inkos-cyan">Simulations</span>
            </h1>
            <p className="text-sm text-muted-foreground">
              Safe, isolated what-if testing — {simulations?.length ?? 0} runs
            </p>
          </div>
        </div>
        <Button
          onClick={() => setShowScenarios(!showScenarios)}
          className="bg-inkos-cyan/15 text-inkos-cyan hover:bg-inkos-cyan/25 border border-inkos-cyan/20"
        >
          {runMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-1.5" />
          )}
          New Simulation
        </Button>
      </motion.div>

      {/* Scenario picker */}
      <AnimatePresence>
        {showScenarios && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Card className="glass border-inkos-cyan/8 mb-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Zap className="h-4 w-4 text-inkos-cyan opacity-70" />
                  Available Scenarios
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!scenarios || scenarios.length === 0 ? (
                  <EmptyState
                    icon={FlaskConical}
                    title="No scenarios available"
                    description="Prime will suggest what-if scenarios once the backend is running and system activity is recorded."
                  />
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {scenarios.map((scenario) => (
                      <ScenarioCard
                        key={scenario.id}
                        scenario={scenario}
                        onRun={() => handleRun(scenario)}
                        isRunning={runMutation.isPending}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Simulation runs list */}
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
            <SkeletonCard lines={5} />
          </div>
        ) : !simulations || simulations.length === 0 ? (
          <Card className="glass border-inkos-cyan/8">
            <CardContent>
              <EmptyState
                icon={FlaskConical}
                title="No simulations yet"
                description='Click "New Simulation" to run a what-if scenario and explore potential changes safely.'
                action={
                  <Button
                    onClick={() => setShowScenarios(true)}
                    size="sm"
                    className="bg-inkos-cyan/15 text-inkos-cyan hover:bg-inkos-cyan/25 border border-inkos-cyan/20"
                  >
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                    Run Your First Simulation
                  </Button>
                }
              />
            </CardContent>
          </Card>
        ) : (
          simulations.map((sim) => (
            <SimulationCard
              key={sim.id}
              simulation={sim}
              expanded={expanded === sim.id}
              onToggle={() =>
                setExpanded(expanded === sim.id ? null : sim.id)
              }
              onRollback={() => handleRollback(sim.id)}
              isRollingBack={rollbackMutation.isPending}
              comparison={
                compareId === sim.id ? comparison ?? null : null
              }
              onCompare={() =>
                setCompareId(compareId === sim.id ? null : sim.id)
              }
            />
          ))
        )}
      </motion.div>
    </div>
  );
}

function ScenarioCard({
  scenario,
  onRun,
  isRunning,
}: {
  scenario: WhatIfScenario;
  onRun: () => void;
  isRunning: boolean;
}) {
  return (
    <div className="glass rounded-lg p-4 border border-inkos-cyan/8 space-y-3 glass-hover">
      <div className="flex items-center gap-2">
        <Badge
          variant="outline"
          className={cn(
            "text-[10px] shrink-0",
            SCENARIO_TYPE_COLOURS[scenario.scenario_type] ??
              "border-white/[0.06] text-muted-foreground",
          )}
        >
          {scenario.scenario_type.replace(/_/g, " ")}
        </Badge>
        <Badge
          variant="outline"
          className={cn(
            "text-[10px] shrink-0",
            scenario.risk_level === "low"
              ? "border-emerald-500/20 text-emerald-400"
              : scenario.risk_level === "medium"
                ? "border-amber-400/20 text-amber-400"
                : "border-red-400/20 text-red-400",
          )}
        >
          {scenario.risk_level}
        </Badge>
      </div>
      <p className="text-sm font-medium">{scenario.name}</p>
      <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
        {scenario.description}
      </p>
      <Button
        size="sm"
        className="w-full bg-inkos-cyan/10 text-inkos-cyan hover:bg-inkos-cyan/20 border border-inkos-cyan/15 text-xs"
        onClick={onRun}
        disabled={isRunning}
      >
        {isRunning ? (
          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
        ) : (
          <Play className="h-3 w-3 mr-1" />
        )}
        Run Simulation
      </Button>
    </div>
  );
}

function SimulationCard({
  simulation,
  expanded,
  onToggle,
  onRollback,
  isRollingBack,
  comparison,
  onCompare,
}: {
  simulation: SimulationRun;
  expanded: boolean;
  onToggle: () => void;
  onRollback: () => void;
  isRollingBack: boolean;
  comparison: {
    deltas: OutcomeDelta[];
    overall_assessment: string;
    recommendation: string;
    summary: string;
  } | null;
  onCompare: () => void;
}) {
  const config = SIM_STATUS_CONFIG[simulation.status];
  const isRunning = simulation.status === "running";
  const StatusIcon = isRunning ? Loader2 : config.icon;
  const result = simulation.result;

  return (
    <Card className="glass glass-hover border-inkos-cyan/8 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-inkos-cyan/[0.02] transition-colors duration-150"
      >
        <StatusIcon
          className={cn(
            "h-5 w-5 shrink-0",
            isRunning && "animate-spin text-inkos-cyan",
            config.colour.split(" ")[1],
          )}
        />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">
            {simulation.scenario.name}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {simulation.scenario.scenario_type.replace(/_/g, " ")} ·{" "}
            {formatDistanceToNow(new Date(simulation.created_at), {
              addSuffix: true,
            })}
            {result && ` · ${result.duration_seconds.toFixed(2)}s`}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge
            variant="outline"
            className={cn("text-[10px]", config.colour)}
          >
            {config.label}
          </Badge>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      <AnimatePresence>
        {expanded && result && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Separator className="bg-white/[0.04]" />
            <div className="px-5 py-4 space-y-4 text-sm">
              {/* Metrics */}
              {Object.keys(result.metrics).length > 0 && (
                <div>
                  <h4 className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
                    <BarChart3 className="h-3.5 w-3.5" />
                    Metrics
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(result.metrics).map(([key, value]) => (
                      <div
                        key={key}
                        className="rounded-lg bg-white/[0.02] px-3 py-2 border border-white/[0.04]"
                      >
                        <p className="text-[10px] text-muted-foreground uppercase tracking-widest">
                          {key.replace(/_/g, " ")}
                        </p>
                        <p className="text-lg font-bold tabular-nums">
                          {typeof value === "number"
                            ? value.toFixed(2)
                            : value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Outcome probabilities */}
              {Object.keys(result.outcome_probabilities).length > 0 && (
                <div>
                  <h4 className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground mb-2">
                    Outcome Probabilities
                  </h4>
                  <div className="space-y-1.5">
                    {Object.entries(result.outcome_probabilities).map(
                      ([key, value]) => (
                        <div key={key} className="flex items-center gap-3">
                          <span className="text-xs text-muted-foreground w-32 truncate">
                            {key.replace(/_/g, " ")}
                          </span>
                          <div className="flex-1 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                            <div
                              className={cn(
                                "h-full rounded-full transition-all duration-500",
                                key.includes("success")
                                  ? "bg-inkos-cyan"
                                  : "bg-red-400/50",
                              )}
                              style={{
                                width: `${Math.round(value * 100)}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs tabular-nums w-12 text-right text-muted-foreground">
                            {Math.round(value * 100)}%
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              )}

              {/* Decision trace */}
              {result.decision_trace.length > 0 && (
                <details className="group">
                  <summary className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground cursor-pointer hover:text-foreground transition-colors flex items-center gap-1.5">
                    Decision Trace ({result.decision_trace.length} steps)
                  </summary>
                  <pre className="mt-2 text-[11px] font-mono text-muted-foreground/60 bg-white/[0.02] rounded-lg p-3 overflow-x-auto max-h-40 border border-white/[0.03]">
                    {JSON.stringify(result.decision_trace, null, 2)}
                  </pre>
                </details>
              )}

              {/* Error */}
              {result.error_message && (
                <div className="flex items-start gap-2 text-xs text-red-400 bg-red-400/[0.04] rounded-md px-3 py-2 border border-red-400/12">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  {result.error_message}
                </div>
              )}

              {/* Comparison report */}
              {simulation.status === "completed" && (
                <div className="space-y-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className={cn(
                      "border-inkos-cyan/20 text-inkos-cyan hover:bg-inkos-cyan/10 text-xs",
                      comparison && "bg-inkos-cyan/8",
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      onCompare();
                    }}
                  >
                    <BarChart3 className="h-3.5 w-3.5 mr-1.5" />
                    {comparison ? "Hide Comparison" : "Compare vs Baseline"}
                  </Button>
                  {comparison && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="bg-white/[0.02] rounded-lg p-4 space-y-3 border border-inkos-cyan/8"
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={cn(
                            "text-xs font-medium px-2 py-1 rounded-full",
                            comparison.overall_assessment === "positive"
                              ? "bg-emerald-500/8 text-emerald-400"
                              : comparison.overall_assessment === "negative"
                                ? "bg-red-400/8 text-red-400"
                                : comparison.overall_assessment === "mixed"
                                  ? "bg-amber-400/8 text-amber-400"
                                  : "bg-white/[0.03] text-muted-foreground",
                          )}
                        >
                          {comparison.overall_assessment}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {comparison.summary}
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {comparison.deltas.map((d) => (
                          <div
                            key={d.metric}
                            className="flex items-center gap-3 text-xs"
                          >
                            <span className="w-28 text-muted-foreground truncate">
                              {d.metric.replace(/_/g, " ")}
                            </span>
                            <span className="w-10 text-right tabular-nums text-muted-foreground">
                              {d.baseline_value.toFixed(0)}
                            </span>
                            <span className="text-muted-foreground/40">→</span>
                            <span
                              className={cn(
                                "w-10 text-right tabular-nums font-medium",
                                d.improved
                                  ? "text-emerald-400"
                                  : d.delta !== 0
                                    ? "text-red-400"
                                    : "text-muted-foreground",
                              )}
                            >
                              {d.simulation_value.toFixed(0)}
                            </span>
                            {d.improved ? (
                              <ArrowUpRight className="h-3 w-3 text-emerald-400" />
                            ) : d.delta < 0 ? (
                              <ArrowDownRight className="h-3 w-3 text-red-400" />
                            ) : (
                              <Minus className="h-3 w-3 text-muted-foreground" />
                            )}
                          </div>
                        ))}
                      </div>
                      {comparison.recommendation && (
                        <p className="text-xs text-muted-foreground italic border-t border-white/[0.04] pt-2">
                          {comparison.recommendation}
                        </p>
                      )}
                    </motion.div>
                  )}
                </div>
              )}

              {/* Rollback button */}
              {simulation.status === "completed" && (
                <div className="pt-1">
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-white/[0.06] text-muted-foreground hover:bg-white/[0.03] hover:text-foreground"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRollback();
                    }}
                    disabled={isRollingBack}
                  >
                    {isRollingBack ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                    )}
                    Rollback
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
