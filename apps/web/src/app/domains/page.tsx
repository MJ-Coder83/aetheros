"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Layers,
  Sparkles,
  Users,
  Wrench,
  GitBranch,
  Shield,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Types ───────────────────────────────────────────────────── */

interface AgentBp {
  agent_id: string;
  name: string;
  role: string;
  goal: string;
  backstory: string;
  capabilities: string[];
}

interface SkillBp {
  skill_id: string;
  name: string;
  description: string;
  is_reused: boolean;
}

interface WorkflowBp {
  workflow_id: string;
  name: string;
  workflow_type: string;
  description: string;
  steps: string[];
  agent_ids: string[];
}

interface DomainConfig {
  max_agents: number;
  requires_human_approval: boolean;
  priority_level: string;
}

interface Blueprint {
  id: string;
  domain_name: string;
  domain_id: string;
  description: string;
  source_description: string;
  agents: AgentBp[];
  skills: SkillBp[];
  workflows: WorkflowBp[];
  config: DomainConfig;
  status: string;
  validation_errors: string[];
  validation_warnings: string[];
  created_at: string;
}

/* ── Icon helpers ────────────────────────────────────────────── */

const roleIcons: Record<string, React.ReactNode> = {
  coordinator: <Shield className="h-4 w-4 text-inkos-cyan" />,
  analyst: <Sparkles className="h-4 w-4 text-inkos-cyan" />,
  executor: <Wrench className="h-4 w-4 text-emerald-400" />,
  reviewer: <CheckCircle2 className="h-4 w-4 text-amber-400" />,
  researcher: <Layers className="h-4 w-4 text-inkos-cyan" />,
  specialist: <Sparkles className="h-4 w-4 text-inkos-cyan" />,
  monitor: <Clock className="h-4 w-4 text-amber-400" />,
  communicator: <Users className="h-4 w-4 text-emerald-400" />,
};

const statusColors: Record<string, string> = {
  draft: "bg-amber-500/20 text-amber-400 border-amber-400/30",
  proposed: "bg-inkos-cyan/20 text-inkos-cyan border-inkos-cyan/30",
  active: "bg-emerald-500/20 text-emerald-400 border-emerald-400/30",
};

/* ── Blueprint preview ───────────────────────────────────────── */

function BlueprintPreview({ blueprint }: { blueprint: Blueprint }) {
  const [openSection, setOpenSection] = useState<string | null>("agents");

  const toggle = (section: string) =>
    setOpenSection(openSection === section ? null : section);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-xl border border-inkos-cyan/8 overflow-hidden"
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-inkos-cyan/4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="h-5 w-5 text-inkos-cyan shrink-0" />
            <h3 className="text-lg font-semibold truncate">
              {blueprint.domain_name}
            </h3>
            <span
              className={cn(
                "text-[10px] font-medium uppercase px-1.5 py-0.5 rounded border",
                statusColors[blueprint.status] ?? "bg-muted text-muted-foreground",
              )}
            >
              {blueprint.status}
            </span>
          </div>
          <p className="text-xs font-mono text-muted-foreground">
            {blueprint.domain_id}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {blueprint.description}
          </p>
        </div>
      </div>

      {/* Stats bar */}
      <div className="px-5 py-3 flex gap-4 border-b border-inkos-cyan/4 bg-inkos-navy-800/20">
        <div className="flex items-center gap-1.5 text-xs">
          <Users className="h-3.5 w-3.5 text-inkos-cyan" />
          <span className="font-medium">{blueprint.agents.length}</span>
          <span className="text-muted-foreground">agents</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Wrench className="h-3.5 w-3.5 text-inkos-cyan" />
          <span className="font-medium">{blueprint.skills.length}</span>
          <span className="text-muted-foreground">skills</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <GitBranch className="h-3.5 w-3.5 text-emerald-400" />
          <span className="font-medium">{blueprint.workflows.length}</span>
          <span className="text-muted-foreground">workflows</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs ml-auto">
          <Shield className="h-3.5 w-3.5" />
          <span
            className={cn(
              "font-medium",
              blueprint.config.priority_level === "critical"
                ? "text-red-400"
                : blueprint.config.priority_level === "high"
                  ? "text-amber-400"
                  : "text-muted-foreground",
            )}
          >
            {blueprint.config.priority_level}
          </span>
        </div>
      </div>

      {/* Collapsible sections */}
      <div className="divide-y divide-white/[0.03]">
        {/* Agents section */}
        <button
          onClick={() => toggle("agents")}
          className="w-full px-5 py-3 flex items-center justify-between text-left hover:bg-inkos-cyan/[0.02] transition-colors"
        >
          <span className="text-sm font-medium flex items-center gap-2">
            <Users className="h-4 w-4 text-inkos-cyan" />
            Agents ({blueprint.agents.length})
          </span>
          {openSection === "agents" ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
        <AnimatePresence>
          {openSection === "agents" && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="px-5 pb-3 space-y-2">
                {blueprint.agents.map((agent) => (
                  <div
                    key={agent.agent_id}
                    className="rounded-lg bg-inkos-navy-800/30 border border-inkos-cyan/4 p-3"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {roleIcons[agent.role] ?? <Users className="h-4 w-4" />}
                      <span className="text-sm font-medium">{agent.name}</span>
                      <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-inkos-cyan/[0.04] text-inkos-cyan border border-inkos-cyan/8">
                        {agent.role}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{agent.goal}</p>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {agent.capabilities.map((c) => (
                        <span
                          key={c}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-inkos-navy-800/40 text-muted-foreground border border-inkos-cyan/4"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Skills section */}
        <button
          onClick={() => toggle("skills")}
          className="w-full px-5 py-3 flex items-center justify-between text-left hover:bg-inkos-cyan/[0.02] transition-colors"
        >
          <span className="text-sm font-medium flex items-center gap-2">
            <Wrench className="h-4 w-4 text-inkos-cyan" />
            Skills ({blueprint.skills.length})
          </span>
          {openSection === "skills" ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
        <AnimatePresence>
          {openSection === "skills" && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="px-5 pb-3 flex flex-wrap gap-2">
                {blueprint.skills.map((skill) => (
                  <span
                    key={skill.skill_id}
                    className={cn(
                      "inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border",
                      skill.is_reused
                        ? "bg-inkos-cyan/10 border-inkos-cyan/20 text-inkos-cyan"
                        : "bg-inkos-cyan/[0.04] border-inkos-cyan/8 text-inkos-cyan",
                    )}
                  >
                    {skill.is_reused && (
                      <span className="text-[9px] uppercase opacity-60">reused</span>
                    )}
                    {skill.name}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Workflows section */}
        <button
          onClick={() => toggle("workflows")}
          className="w-full px-5 py-3 flex items-center justify-between text-left hover:bg-inkos-cyan/[0.02] transition-colors"
        >
          <span className="text-sm font-medium flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-emerald-400" />
            Workflows ({blueprint.workflows.length})
          </span>
          {openSection === "workflows" ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
        <AnimatePresence>
          {openSection === "workflows" && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="px-5 pb-3 space-y-2">
                {blueprint.workflows.map((wf) => (
                  <div
                    key={wf.workflow_id}
                    className="rounded-lg bg-inkos-navy-800/30 border border-inkos-cyan/4 p-3"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <GitBranch className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-sm font-medium">{wf.name}</span>
                      <span className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-400/20">
                        {wf.workflow_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                      {wf.steps.map((step, i) => (
                        <span key={i} className="flex items-center gap-1.5">
                          <span className="text-xs px-2 py-0.5 rounded bg-inkos-navy-800/60 text-muted-foreground">
                            {step}
                          </span>
                          {i < wf.steps.length - 1 && (
                            <span className="text-muted-foreground/40">→</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Validation */}
      {(blueprint.validation_errors.length > 0 ||
        blueprint.validation_warnings.length > 0) && (
        <div className="px-5 py-3 border-t border-inkos-cyan/4 space-y-1">
          {blueprint.validation_errors.map((e, i) => (
            <div
              key={`err-${i}`}
              className="flex items-start gap-2 text-xs text-red-400"
            >
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              {e}
            </div>
          ))}
          {blueprint.validation_warnings.map((w, i) => (
            <div
              key={`warn-${i}`}
              className="flex items-start gap-2 text-xs text-amber-400/70"
            >
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              {w}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

/* ── Main page ──────────────────────────────────────────────── */

const EXAMPLE_DESCRIPTIONS = [
  "Create a Legal Research Domain for contract analysis and compliance checking",
  "Build a domain for academic research and literature review",
  "Create a software engineering domain for code review and deployment",
  "Set up a financial operations domain for trading and risk management",
  "Create a healthcare domain for patient care and diagnosis support",
];

export default function DomainsPage() {
  const [description, setDescription] = useState("");
  const [domainName, setDomainName] = useState("");
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setIsGenerating(true);
    setError(null);
    setBlueprint(null);

    try {
      const res = await fetch("/api/domains/blueprint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description.trim(),
          domain_name: domainName.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      const data = (await res.json()) as Blueprint;
      setBlueprint(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreate = async () => {
    if (!description.trim()) return;
    setIsGenerating(true);
    setError(null);
    setBlueprint(null);

    try {
      const res = await fetch("/api/domains/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description.trim(),
          domain_name: domainName.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      const data = (await res.json()) as {
        blueprint: Blueprint;
        message: string;
      };
      setBlueprint(data.blueprint);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8 page-transition">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
          <Layers className="h-8 w-8 text-inkos-cyan text-glow-teal" />
          <span>
            <span className="text-inkos-cyan text-glow-teal">Domain</span>{" "}
            Creator
          </span>
        </h1>
        <p className="text-muted-foreground mt-1">
          Describe a domain in natural language and get a complete, ready-to-use
          domain blueprint with agents, skills, and workflows.
        </p>
      </div>

      {/* Creation form */}
      <div className="glass rounded-xl border border-inkos-cyan/8 p-5 space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Create New Domain
        </h2>

        <div className="space-y-3">
          {/* Domain name (optional) */}
          <input
            type="text"
            value={domainName}
            onChange={(e) => setDomainName(e.target.value)}
            placeholder="Domain name (optional — auto-generated if empty)"
            className="w-full rounded-md border border-inkos-cyan/8 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan"
          />

          {/* Description */}
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder='e.g. "Create a Legal Research Domain for contract analysis and compliance checking"'
            rows={3}
            className="w-full rounded-md border border-inkos-cyan/8 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan resize-none"
          />

          {/* Example chips */}
          <div className="flex flex-wrap gap-1.5">
            <span className="text-[10px] uppercase text-muted-foreground mr-1 self-center">
              Try:
            </span>
            {EXAMPLE_DESCRIPTIONS.map((ex) => (
              <button
                key={ex}
                onClick={() => setDescription(ex)}
                className="text-[10px] px-2 py-1 rounded border border-inkos-cyan/8 text-muted-foreground hover:text-inkos-cyan hover:border-inkos-cyan/20 transition-all truncate max-w-[200px]"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          <button
            onClick={handleGenerate}
            disabled={!description.trim() || isGenerating}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              description.trim() && !isGenerating
                ? "bg-inkos-cyan/80 text-white hover:bg-inkos-cyan"
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
                Preview Blueprint
              </>
            )}
          </button>
          <button
            onClick={handleCreate}
            disabled={!description.trim() || isGenerating}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              description.trim() && !isGenerating
                ? "bg-inkos-cyan/80 text-inkos-navy-900 hover:bg-inkos-cyan"
                : "bg-inkos-navy-800/40 text-muted-foreground cursor-not-allowed",
            )}
          >
            <Layers className="h-4 w-4" />
            Create Domain
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-400/30 bg-red-500/10 p-3">
            <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Blueprint preview */}
      {blueprint && <BlueprintPreview blueprint={blueprint} />}
    </div>
  );
}
