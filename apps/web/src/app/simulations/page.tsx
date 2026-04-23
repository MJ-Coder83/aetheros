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
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useSimulations, useSimulationScenarios, useRunSimulation, useRollbackSimulation } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import type { SimulationRun, SimulationStatus, WhatIfScenario } from "@/types";

const SIM_STATUS_CONFIG: Record<SimulationStatus, { icon: React.ElementType; colour: string; label: string }> = {
  pending: { icon: Clock, colour: "border-amber-400/40 text-amber-400", label: "Pending" },
  running: { icon: Zap, colour: "border-inkos-cyan/40 text-inkos-cyan-400", label: "Running" },
  completed: { icon: CheckCircle2, colour: "border-emerald-400/40 text-emerald-400", label: "Completed" },
  failed: { icon: XCircle, colour: "border-red-400/40 text-red-400", label: "Failed" },
  aborted: { icon: AlertTriangle, colour: "border-amber-400/40 text-amber-400", label: "Aborted" },
  rolled_back: { icon: RotateCcw, colour: "border-muted-foreground/40 text-muted-foreground", label: "Rolled Back" },
};

const SCENARIO_TYPE_COLOURS: Record<string, string> = {
  skill_evolution: "border-inkos-purple/40 text-inkos-purple-400",
  agent_reconfig: "border-inkos-cyan/40 text-inkos-cyan-400",
  domain_change: "border-emerald-400/40 text-emerald-400",
  custom: "border-amber-400/40 text-amber-400",
};

export default function SimulationsPage() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showScenarios, setShowScenarios] = useState(false);
  const { data: simulations, isLoading } = useSimulations();
  const { data: scenarios } = useSimulationScenarios();
  const runMutation = useRunSimulation();
  const rollbackMutation = useRollbackSimulation();

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <FlaskConical className="h-7 w-7 text-inkos-cyan" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-inkos-cyan text-glow-cyan">
              Simulations
            </h1>
            <p className="text-sm text-muted-foreground">
              Safe, isolated what-if testing — {simulations?.length ?? 0} runs
            </p>
          </div>
        </div>
        <Button
          onClick={() => setShowScenarios(!showScenarios)}
          className="bg-inkos-purple hover:bg-inkos-purple-700"
        >
          <Play className="h-4 w-4 mr-1.5" />
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
            <Card className="glass border-inkos-purple/20 mb-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Zap className="h-4 w-4 text-inkos-purple-400" />
                  Available Scenarios
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!scenarios || scenarios.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    No scenarios generated yet. Start the backend and Prime will
                    suggest what-if scenarios.
                  </p>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {scenarios.map((scenario) => (
                      <ScenarioCard
                        key={scenario.id}
                        scenario={scenario}
                        onRun={() => {
                          runMutation.mutate({ scenario, timeout: 60 });
                          setShowScenarios(false);
                        }}
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
        transition={{ delay: 0.1 }}
        className="space-y-3"
      >
        {isLoading ? (
          <div className="space-y-3 animate-pulse">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-24 rounded-xl bg-muted/30" />
            ))}
          </div>
        ) : !simulations || simulations.length === 0 ? (
          <Card className="glass border-inkos-purple/20">
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              No simulations yet. Click &ldquo;New Simulation&rdquo; to run a what-if scenario.
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
              onRollback={() => rollbackMutation.mutate(sim.id)}
              isRollingBack={rollbackMutation.isPending}
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
    <div className="glass rounded-lg p-4 border border-inkos-purple/15 space-y-3">
      <div className="flex items-center gap-2">
        <Badge
          variant="outline"
          className={cn(
            "text-[10px] shrink-0",
            SCENARIO_TYPE_COLOURS[scenario.scenario_type] ??
              "border-border text-muted-foreground",
          )}
        >
          {scenario.scenario_type.replace(/_/g, " ")}
        </Badge>
        <Badge
          variant="outline"
          className={cn(
            "text-[10px] shrink-0",
            scenario.risk_level === "low"
              ? "border-emerald-400/30 text-emerald-400"
              : scenario.risk_level === "medium"
                ? "border-amber-400/30 text-amber-400"
                : "border-red-400/30 text-red-400",
          )}
        >
          {scenario.risk_level}
        </Badge>
      </div>
      <p className="text-sm font-medium">{scenario.name}</p>
      <p className="text-xs text-muted-foreground line-clamp-2">
        {scenario.description}
      </p>
      <Button
        size="sm"
        className="w-full bg-inkos-purple/80 hover:bg-inkos-purple text-xs"
        onClick={onRun}
        disabled={isRunning}
      >
        <Play className="h-3 w-3 mr-1" />
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
}: {
  simulation: SimulationRun;
  expanded: boolean;
  onToggle: () => void;
  onRollback: () => void;
  isRollingBack: boolean;
}) {
  const config = SIM_STATUS_CONFIG[simulation.status];
  const StatusIcon = config.icon;
  const result = simulation.result;

  return (
    <Card className="glass border-inkos-purple/20 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-inkos-purple/5 transition-colors"
      >
        <StatusIcon className={cn("h-5 w-5 shrink-0", config.colour.split(" ")[1])} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">
            {simulation.scenario.name}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {simulation.scenario.scenario_type.replace(/_/g, "")} ·{" "}
            {formatDistanceToNow(new Date(simulation.created_at), {
              addSuffix: true,
            })}
            {result && ` · ${result.duration_seconds.toFixed(2)}s`}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
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

      <AnimatePresence>
        {expanded && result && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Separator className="bg-inkos-purple/15" />
            <div className="px-5 py-4 space-y-4 text-sm">
              {/* Metrics */}
              {Object.keys(result.metrics).length > 0 && (
                <div>
                  <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                    <BarChart3 className="h-3.5 w-3.5" /> Metrics
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(result.metrics).map(([key, value]) => (
                      <div
                        key={key}
                        className="rounded-lg bg-inkos-navy-800/50 px-3 py-2"
                      >
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                          {key.replace(/_/g, " ")}
                        </p>
                        <p className="text-lg font-bold tabular-nums">
                          {typeof value === "number" ? value.toFixed(2) : value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Outcome probabilities */}
              {Object.keys(result.outcome_probabilities).length > 0 && (
                <div>
                  <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                    Outcome Probabilities
                  </h4>
                  <div className="space-y-1.5">
                    {Object.entries(result.outcome_probabilities).map(
                      ([key, value]) => (
                        <div key={key} className="flex items-center gap-3">
                          <span className="text-xs text-muted-foreground w-32 truncate">
                            {key.replace(/_/g, " ")}
                          </span>
                          <div className="flex-1 h-2 rounded-full bg-inkos-navy-800 overflow-hidden">
                            <div
                              className={cn(
                                "h-full rounded-full",
                                key.includes("success")
                                  ? "bg-inkos-cyan"
                                  : "bg-red-400/60",
                              )}
                              style={{
                                width: `${Math.round(value * 100)}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs tabular-nums w-12 text-right">
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
                <div>
                  <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                    Decision Trace
                  </h4>
                  <pre className="text-[11px] font-mono text-muted-foreground/70 bg-inkos-navy-800/50 rounded-lg p-3 overflow-x-auto max-h-40">
                    {JSON.stringify(result.decision_trace, null, 2)}
                  </pre>
                </div>
              )}

              {/* Error */}
              {result.error_message && (
                <div className="flex items-start gap-2 text-xs text-red-400 bg-red-400/5 rounded-md px-3 py-2 border border-red-400/20">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  {result.error_message}
                </div>
              )}

              {/* Rollback button */}
              {simulation.status === "completed" && (
                <div className="pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-inkos-purple/30 text-inkos-purple-400 hover:bg-inkos-purple/10"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRollback();
                    }}
                    disabled={isRollingBack}
                  >
                    <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
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
