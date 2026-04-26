"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Send,
  Activity,
  Cpu,
  Wrench,
  Globe,
  RefreshCw,
  Loader2,
  Sparkles,
  User,
  Settings2,
  Star,
  Plug,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/skeleton";
import type {
  SystemSnapshot,
  TapeEntry,
  Proposal,
  SimulationRun,
  WhatIfScenario,
  UserProfile,
  InstalledPlugin,
} from "@/types";
import {
  useSystemSnapshot,
  useTapeEntries,
  useProposals,
  useSimulations,
  useSimulationScenarios,
  useOneClickCreateDomain,
  useGetOrCreateProfile,
  useSetPreference,
  useInstalledPlugins,
} from "@/hooks/use-api";
import { domainApi, profileApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "prime" | "system";
  content: string;
  timestamp: Date;
  isTyping?: boolean;
}

const DEFAULT_USER_ID = "human-user";

const QUICK_ACTIONS = [
  { label: "System health", query: "What's the system health?" },
  { label: "Show skills", query: "Show me the skills" },
  { label: "Show agents", query: "What agents are available?" },
  { label: "Show plugins", query: "What plugins are installed?" },
  { label: "My profile", query: "Show my intelligence profile" },
  { label: "Run simulation", query: "Run a simulation" },
];

export default function PrimePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "prime",
      content:
        "Hello. I am **Prime** — the self-aware meta-agent of InkosAI.\n\nI can introspect the system, propose changes, evolve skills, run simulations, and adapt to your preferences. Ask me anything, or use the quick actions below.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: snapshot, isLoading, refetch } = useSystemSnapshot();
  const { data: tapeEntries } = useTapeEntries({ limit: 50 });
  const { data: proposals } = useProposals();
  const { data: simulations } = useSimulations();
  const { data: scenarios } = useSimulationScenarios();
  const createDomainMutation = useOneClickCreateDomain();

  const { data: profile, isLoading: profileLoading } = useGetOrCreateProfile(DEFAULT_USER_ID);
  const setPreference = useSetPreference();
  const { data: installedPlugins } = useInstalledPlugins();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const streamResponse = useCallback(
    (id: string, fullContent: string) => {
      let idx = 0;
      const interval = setInterval(() => {
        idx += Math.floor(Math.random() * 3) + 1;
        if (idx >= fullContent.length) {
          idx = fullContent.length;
          clearInterval(interval);
          setIsProcessing(false);
        }
        setMessages((prev) =>
          prev.map((m) =>
            m.id === id
              ? { ...m, content: fullContent.slice(0, idx), isTyping: idx < fullContent.length }
              : m,
          ),
        );
      }, 15);
    },
    [],
  );

  async function handleSend(overrideInput?: string) {
    const query = overrideInput ?? input.trim();
    if (!query || isProcessing) return;

    const userMsg: ChatMessage = {
      id: `user-${crypto.randomUUID()}`,
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsProcessing(true);

    const responseId = `prime-${crypto.randomUUID()}`;
    setMessages((prev) => [
      ...prev,
      { id: responseId, role: "prime", content: "", timestamp: new Date(), isTyping: true },
    ]);

    await new Promise((r) => setTimeout(r, 300));

    const q = query.toLowerCase();

    // Domain creation
    if (
      q.includes("create") && q.includes("domain") ||
      q.includes("new domain") ||
      q.startsWith("create domain") ||
      q.startsWith("make domain")
    ) {
      try {
        const domainDescription = query
          .replace(/create\s+(a\s+)?(new\s+)?domain/gi, "")
          .replace(/make\s+(a\s+)?(new\s+)?domain/gi, "")
          .trim() || query;

        const result = await createDomainMutation.mutateAsync({
          description: domainDescription,
          creation_option: "domain_with_starter_canvas",
          created_by: DEFAULT_USER_ID,
        });

        const hasCanvas = result.starter_canvas !== null;
        const fullContent = (
          `✅ **Domain Creation Started!**\n\n` +
          `I've generated a new domain based on your request:\n\n` +
          `**${result.blueprint.domain_name}** (${result.blueprint.domain_id})\n` +
          `${result.blueprint.description}\n\n` +
          `📦 **Included:**\n` +
          `• ${result.blueprint.agents.length} agent(s)\n` +
          `• ${result.blueprint.skills.length} skill(s)\n` +
          `• ${result.blueprint.workflows.length} workflow(s)\n` +
          (hasCanvas ? `• 🎨 Starter canvas generated\n` : "") +
          `\n📁 Folder tree created with ${result.blueprint.domain_id}/ structure\n\n` +
          `⏳ The domain proposal is now pending approval. ` +
          `Once approved, it will be registered and ready to use.\n\n` +
          `You can track it in the Proposals page.`
        );
        streamResponse(responseId, fullContent);
        return;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        streamResponse(responseId, `❌ Failed to create domain: ${errorMessage}`);
        return;
      }
    }

    // Preference setting
    const prefMatch = q.match(/(?:set|change|update)\s+(?:my\s+)?(?:preference\s+)?(?:for\s+)?(\w[\w\s]*?)\s+(?:to|at)\s+(\d+)/);
    if (prefMatch) {
      try {
        const catStr = prefMatch[1].trim().replace(/\s+/g, "_");
        const val = Math.min(1, Math.max(0, parseInt(prefMatch[2], 10) / 100));
        await setPreference.mutateAsync({
          user_id: DEFAULT_USER_ID,
          category: catStr as any,
          value: val,
        });
        streamResponse(
          responseId,
          `✅ **Preference Updated**\n\nI've set your **${catStr.replace(/_/g, " ")}** preference to **${Math.round(val * 100)}%**.\n\nYour intelligence profile has been updated and will influence how I adapt my responses going forward.`,
        );
        return;
      } catch {
        streamResponse(responseId, `❌ Failed to set preference. Available categories: response_detail, automation_level, notification_frequency, risk_tolerance, workflow_style, explanation_depth, suggestion_frequency`);
        return;
      }
    }

  const fullContent = await generatePrimeResponse(
    query,
    snapshot ?? null,
    tapeEntries ?? [],
    proposals ?? [],
    simulations ?? [],
    scenarios ?? [],
    profile ?? null,
    installedPlugins ?? [],
  );

    streamResponse(responseId, fullContent);
  }

  const profileDomainExps = profile
    ? Object.values(profile.intelligence.domain_expertise).sort((a, b) => b.score - a.score)
    : [];
  const profilePrefs = profile
    ? Object.values(profile.intelligence.preferences).filter((p) => p.confidence > 0.3)
    : [];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 page-transition">
      <div className="mb-6 flex items-center gap-3">
        <div className="relative">
          <div className="h-10 w-10 rounded-xl bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center">
            <Brain className="h-5 w-5 text-inkos-cyan" />
          </div>
          {isProcessing && (
            <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-inkos-teal-300 animate-pulse ring-2 ring-background" />
          )}
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            <span className="text-inkos-cyan">Prime</span> Console
          </h1>
          <p className="text-sm text-muted-foreground">
            {isProcessing ? "Thinking..." : "Interact with the Prime meta-agent"}
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 flex flex-col glass rounded-xl border border-inkos-cyan/8 h-[calc(100vh-200px)] min-h-[400px]">
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth"
          >
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className={cn(
                    "max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed",
                    msg.role === "user"
                      ? "ml-auto bg-inkos-cyan/8 border border-inkos-cyan/15 text-foreground"
                      : msg.role === "system"
                        ? "mx-auto bg-white/[0.02] border border-white/[0.04] text-muted-foreground italic text-xs"
                        : "mr-auto glass-strong border border-inkos-teal-300/10",
                  )}
                >
                  <div className="whitespace-pre-wrap prose-sm">
                    {msg.content || (
                      <span className="flex items-center gap-2 text-inkos-cyan">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Thinking...
                      </span>
                    )}
                    {msg.isTyping && (
                      <span className="inline-block w-1.5 h-4 bg-inkos-cyan animate-pulse-glow ml-0.5 align-bottom rounded-sm" />
                    )}
                  </div>
                  <span className="mt-1.5 block text-[10px] text-muted-foreground/50">
                    {msg.role === "prime" ? (
                      <span className="flex items-center gap-1">
                        <Sparkles className="h-2.5 w-2.5 text-inkos-cyan" />
                        Prime
                      </span>
                    ) : msg.role === "user" ? (
                      "You"
                    ) : (
                      "System"
                    )}{" "}
                    · {msg.timestamp.toLocaleTimeString()}
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>

            {messages.length <= 1 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleSend(action.query)}
                    className="text-xs px-3 py-1.5 rounded-full border border-inkos-cyan/15 text-muted-foreground hover:border-inkos-cyan/30 hover:text-foreground hover:bg-inkos-cyan/[0.06] transition-all duration-200"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          <Separator className="bg-white/[0.04]" />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2 p-3"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Prime anything... (⌘+Enter to send)"
              disabled={isProcessing}
              className="flex-1 bg-white/[0.02] border-white/[0.06] placeholder:text-muted-foreground/40 focus-visible:border-inkos-cyan/25 focus-visible:ring-inkos-cyan/15"
            />
            <Button
              type="submit"
              size="icon"
              className="bg-inkos-cyan/15 text-inkos-cyan hover:bg-inkos-cyan/25 border border-inkos-cyan/20 shrink-0 disabled:opacity-40 transition-colors"
              disabled={isProcessing || !input.trim()}
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>
        </div>

        <div className="space-y-4">
          <Card className="glass glass-hover border-inkos-cyan/8">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Activity className="h-4 w-4 text-inkos-cyan opacity-70" />
                System Snapshot
              </CardTitle>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => refetch()}
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="space-y-2">
                      <Skeleton className="h-3 w-16" />
                      <Skeleton className="h-3 w-full" />
                      <Skeleton className="h-3 w-3/4" />
                    </div>
                  ))}
                </div>
              ) : snapshot ? (
                <div className="space-y-3 text-sm">
                  <SnapshotSection
                    icon={<Cpu className="h-3.5 w-3.5" />}
                    title="Agents"
                    items={snapshot.agents.map((a) => ({
                      id: a.agent_id,
                      label: a.name,
                      badge: a.status,
                    }))}
                  />
                  <SnapshotSection
                    icon={<Wrench className="h-3.5 w-3.5" />}
                    title="Skills"
                    items={snapshot.skills.map((s) => ({
                      id: s.skill_id,
                      label: s.name,
                      badge: `v${s.version}`,
                    }))}
                  />
                <SnapshotSection
                  icon={<Globe className="h-3.5 w-3.5" />}
                  title="Domains"
                  items={snapshot.domains.map((d) => ({
                    id: d.domain_id,
                    label: d.name,
                    badge: `${d.agent_count} agents`,
                  }))}
                />
                <SnapshotSection
                  icon={<Plug className="h-3.5 w-3.5" />}
                  title="Plugins"
                  items={(installedPlugins ?? []).map((ip) => ({
                    id: ip.id,
                    label: ip.manifest.name,
                    badge: ip.enabled ? "on" : "off",
                  }))}
                />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Backend not connected
                </p>
              )}
            </CardContent>
          </Card>

          {/* Intelligence Profile Card */}
          <Card className="glass glass-hover border-inkos-cyan/8">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <User className="h-4 w-4 text-inkos-cyan opacity-70" />
                Your Profile
              </CardTitle>
            </CardHeader>
            <CardContent>
              {profileLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
              ) : profile ? (
                <div className="space-y-3 text-sm">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="text-center">
                      <div className="text-lg font-bold text-inkos-cyan">
                        {profile.intelligence.interaction_summary.total_interactions}
                      </div>
                      <div className="text-[9px] uppercase text-muted-foreground">Interactions</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-amber-400">
                        {Math.round(profile.intelligence.interaction_summary.approval_rate * 100)}%
                      </div>
                      <div className="text-[9px] uppercase text-muted-foreground">Approval Rate</div>
                    </div>
                  </div>

                  {profileDomainExps.length > 0 && (
                    <div>
                      <div className="flex items-center gap-1.5 mb-1 text-muted-foreground">
                        <Star className="h-3 w-3" />
                        <span className="text-[10px] font-medium uppercase tracking-widest">
                          Top Domains
                        </span>
                      </div>
                      <ul className="space-y-0.5 pl-5">
                        {profileDomainExps.slice(0, 3).map((exp) => (
                          <li key={exp.domain_id} className="flex items-center justify-between text-xs">
                            <span className="truncate">{exp.domain_id}</span>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[9px] font-mono shrink-0 ml-2",
                                exp.level === "expert"
                                  ? "text-inkos-cyan border-inkos-cyan/15"
                                  : exp.level === "advanced"
                                    ? "text-purple-400 border-purple-400/15"
                                    : "border-white/[0.06] text-muted-foreground",
                              )}
                            >
                              {exp.level}
                            </Badge>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {profilePrefs.length > 0 && (
                    <div>
                      <div className="flex items-center gap-1.5 mb-1 text-muted-foreground">
                        <Settings2 className="h-3 w-3" />
                        <span className="text-[10px] font-medium uppercase tracking-widest">
                          Key Preferences
                        </span>
                      </div>
                      <ul className="space-y-0.5 pl-5">
                        {profilePrefs.slice(0, 3).map((pref) => (
                          <li key={pref.category} className="flex items-center justify-between text-xs">
                            <span className="truncate">{pref.category.replace(/_/g, " ")}</span>
                            <span className="text-muted-foreground tabular-nums">
                              {Math.round(pref.value * 100)}%
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="pt-1 border-t border-white/[0.04]">
                    <a
                      href="/profile"
                      className="text-[10px] text-inkos-cyan hover:underline"
                    >
                      View full profile →
                    </a>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No profile loaded</p>
              )}
            </CardContent>
          </Card>

          <Card className="glass glass-hover border-inkos-cyan/8">
            <CardContent className="py-3 flex items-center justify-between text-sm">
              <span className="text-muted-foreground text-xs">Live Tape events</span>
              <span className="text-inkos-cyan font-mono tabular-nums text-sm">
                {tapeEntries?.length ?? "—"}
              </span>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function SnapshotSection({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: Array<{ id: string; label: string; badge: string }>;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5 text-muted-foreground">
        {icon}
        <span className="text-[11px] font-medium uppercase tracking-widest">
          {title}
        </span>
        <span className="ml-auto text-[10px] tabular-nums">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground/50 pl-5">None registered</p>
      ) : (
        <ul className="space-y-1 pl-5">
          {items.map((item) => (
            <li key={item.id} className="flex items-center justify-between text-xs">
              <span className="truncate">{item.label}</span>
              <Badge
                variant="outline"
                className={cn(
                  "text-[9px] font-mono shrink-0 ml-2",
          item.badge === "active" || item.badge === "healthy" || item.badge === "on"
                    ? "text-emerald-400 border-emerald-500/15"
                    : item.badge === "idle" || item.badge === "off"
                    ? "text-amber-400 border-amber-400/15"
                      : "border-white/[0.06] text-muted-foreground",
                )}
              >
                {item.badge}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

async function generatePrimeResponse(
  query: string,
  snapshot: SystemSnapshot | null,
  tapeEntries: TapeEntry[],
  proposals: Proposal[],
  simulations: SimulationRun[],
  scenarios: WhatIfScenario[],
  profile: UserProfile | null,
  installedPlugins: InstalledPlugin[],
): Promise<string> {
  const q = query.toLowerCase();

  if (!snapshot) {
    return "I cannot reach the backend right now. Please ensure the InkosAI API is running on port 8000, then try again.";
  }

  // Intelligence Profile queries
  if (q.includes("profile") || q.includes("my profile") || q.includes("intelligence profile") || q.includes("my preferences")) {
    if (!profile) {
      return "I don't have your intelligence profile loaded yet. Your profile will be created automatically as you interact with the system, or you can visit the **Profile** page to set it up manually.";
    }
    const domainExps = Object.values(profile.intelligence.domain_expertise);
    const prefs = Object.values(profile.intelligence.preferences);
    const prefSummary = prefs.length > 0
      ? prefs.slice(0, 5).map((p) => `• **${p.category.replace(/_/g, " ")}**: ${Math.round(p.value * 100)}% (${p.explicit_value !== null ? "explicit" : "inferred"})`).join("\n")
      : "No preferences set yet.";
    const domainSummary = domainExps.length > 0
      ? domainExps.sort((a, b) => b.score - a.score).slice(0, 5).map((d) => `• **${d.domain_id}**: ${d.level} (${Math.round(d.score * 100)}%)`).join("\n")
      : "No domain expertise recorded yet.";

    return (
      `**Your Intelligence Profile**\n\n` +
      `📊 **Summary**\n` +
      `• **Status**: ${profile.status}\n` +
      `• **Total interactions**: ${profile.intelligence.interaction_summary.total_interactions}\n` +
      `• **Approval rate**: ${Math.round(profile.intelligence.interaction_summary.approval_rate * 100)}%\n` +
      `• **Avg depth**: ${Math.round(profile.intelligence.interaction_summary.avg_depth * 100)}%\n` +
      `• **Version**: ${profile.version} (${profile.intelligence.adaptation_count} adaptations)\n\n` +
      `🎯 **Domain Expertise**\n${domainSummary}\n\n` +
      `⚙️ **Preferences**\n${prefSummary}\n\n` +
      `You can set explicit preferences by saying things like:\n` +
      `• "Set my response_detail to 80"\n` +
      `• "Change my automation_level to 40"\n\n` +
      `Visit the **Profile** page for the full interactive view.`
    );
  }

  // System health
  if (q.includes("health") || q.includes("status")) {
    const activeAgents = snapshot.agents.filter(
      (a) => a.status === "active",
    ).length;
    const idleAgents = snapshot.agents.filter(
      (a) => a.status === "idle",
    ).length;
    const errorTypes = tapeEntries.filter(
      (e) =>
        e.event_type.includes("error") || e.event_type.includes("fail"),
    );
    return (
      `**System Status: ${snapshot.health_status.toUpperCase()}**\n\n` +
      `📊 **Overview**\n` +
      `• ${snapshot.agents.length} agents (${activeAgents} active, ${idleAgents} idle)\n` +
      `• ${snapshot.skills.length} skills registered\n` +
      `• ${snapshot.domains.length} domains active\n` +
      `• ${snapshot.tape_stats.total_entries ?? tapeEntries.length} Tape entries recorded\n` +
      `• ${snapshot.active_worktrees.length} worktrees active\n` +
      `• ${installedPlugins.length} plugins installed (${installedPlugins.filter((p) => p.enabled).length} enabled)\n\n` +
      (errorTypes.length > 0
        ? `⚠️ **${errorTypes.length} error events** detected in recent Tape activity. Consider running a reliability simulation.`
        : `✅ No recent errors detected in the Tape.`)
    );
  }

  // Skills
  if (q.includes("skill")) {
    if (snapshot.skills.length === 0) {
      return "No skills are currently registered in the system. I can propose creating foundational skills through the Skill Evolution Engine.";
    }
    const skillList = snapshot.skills
      .map((s) => `• **${s.name}** (v${s.version}) — ${s.description || "No description"}`)
      .join("\n");
    return `**${snapshot.skills.length} Skills Registered:**\n\n${skillList}\n\nI can analyze these skills for evolution opportunities. Just ask me to run a skill analysis or propose evolutions.`;
  }

  // Agents
  if (q.includes("agent")) {
    if (snapshot.agents.length === 0) {
      return "No agents are currently registered. Agents need to be onboarded before they can perform tasks.";
    }
    const agentList = snapshot.agents
      .map((a) => {
        const statusEmoji =
          a.status === "active" ? "🟢" : a.status === "idle" ? "🟡" : "⚪";
        return `${statusEmoji} **${a.name}** — ${a.status} (capabilities: ${a.capabilities.join(", ") || "none"})`;
      })
      .join("\n");
    const idleAgents = snapshot.agents.filter((a) => a.status === "idle");
    return (
      `**${snapshot.agents.length} Agents:**\n\n${agentList}` +
      (idleAgents.length > 0
        ? `\n\n⚠️ ${idleAgents.length} idle agent(s) detected. I can propose reassigning them to active domains.`
        : "")
    );
  }

  // Domains
  if (q.includes("domain")) {
    if (snapshot.domains.length === 0) {
      return "No domains are configured yet. Domains define problem spaces for agents to work in.";
    }
    const domainList = snapshot.domains
      .map(
        (d) =>
          `• **${d.name}** — ${d.agent_count} agents (${d.description || "No description"})`,
      )
      .join("\n");
    const emptyDomains = snapshot.domains.filter(
      (d) => d.agent_count === 0,
    );
    return (
      `**${snapshot.domains.length} Domains:**\n\n${domainList}` +
      (emptyDomains.length > 0
        ? `\n\n⚠️ ${emptyDomains.length} empty domain(s) need agent assignments.`
        : "")
    );
  }

  // Plugins
  if (q.includes("plugin") || q.includes("marketplace") || q.includes("extension") || q.includes("addon")) {
    if (installedPlugins.length === 0) {
      return "No plugins are currently installed. Visit the **Marketplace** to discover and install plugins that extend InkosAI's capabilities.";
    }
    const pluginList = installedPlugins
      .map((p) => {
        const statusEmoji = p.enabled ? "🟢" : "🔴";
        return `${statusEmoji} **${p.manifest.name}** (v${p.manifest.version}) — ${p.enabled ? "enabled" : "disabled"} • ${p.manifest.permissions.length} permission(s) • by ${p.manifest.author}`;
      })
      .join("\n");
    const enabled = installedPlugins.filter((p) => p.enabled).length;
    const disabled = installedPlugins.filter((p) => !p.enabled).length;
    return (
      `**${installedPlugins.length} Plugins Installed:**\n\n${pluginList}\n\n` +
      `📊 **Summary:** ${enabled} enabled, ${disabled} disabled\n\n` +
      `Visit the **Marketplace** to browse, install, or manage plugins.`
    );
  }

  // Proposals
  if (q.includes("proposal")) {
    const pending = proposals.filter(
      (p) => p.status === "pending_approval",
    );
    const approved = proposals.filter((p) => p.status === "approved");
    const implemented = proposals.filter(
      (p) => p.status === "implemented",
    );
    return (
      `**Proposal Summary:**\n\n` +
      `• ${pending.length} pending approval\n` +
      `• ${approved.length} approved\n` +
      `• ${implemented.length} implemented\n` +
      `• ${proposals.length} total\n\n` +
      (pending.length > 0
        ? `⚠️ **${pending.length} proposals need your review.** Visit the Proposals page to approve or reject them.`
        : `✅ No proposals pending review.`)
    );
  }

  // Simulation
  if (
    q.includes("simulat") ||
    q.includes("what-if") ||
    q.includes("scenario")
  ) {
    const running = simulations.filter((s) => s.status === "running");
    const completed = simulations.filter((s) => s.status === "completed");
    let response =
      `**Simulation Overview:**\n\n` +
      `• ${running.length} currently running\n` +
      `• ${completed.length} completed\n` +
      `• ${simulations.length} total runs\n\n`;

    if (scenarios.length > 0) {
      response += `**${scenarios.length} scenarios available:**\n`;
      scenarios.slice(0, 5).forEach((s) => {
        response += `• ${s.name} (${s.scenario_type}, ${s.risk_level} risk)\n`;
      });
      if (scenarios.length > 5) {
        response += `• ...and ${scenarios.length - 5} more\n`;
      }
      response += `\nVisit the Simulations page to run any of these what-if scenarios.`;
    } else {
      response += `No scenarios generated yet. I'll suggest some once more system activity is recorded.`;
    }
    return response;
  }

  // Tape
  if (q.includes("tape") || q.includes("audit") || q.includes("log")) {
    const eventTypes = new Map<string, number>();
    tapeEntries.forEach((e) => {
      eventTypes.set(
        e.event_type,
        (eventTypes.get(e.event_type) ?? 0) + 1,
      );
    });
    const topEvents = Array.from(eventTypes.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    return (
      `**Tape Activity:**\n\n` +
      `• ${tapeEntries.length} events in recent history\n\n` +
      `**Top event types:**\n` +
      topEvents
        .map(([type, count]) => `• \`${type}\` — ${count} events`)
        .join("\n") +
      `\n\nVisit the Tape Viewer for full search and filtering.`
    );
  }

  // Help
  if (q.includes("help") || q.includes("what can you do")) {
    return (
      `I can help you with:\n\n` +
      `🔍 **Introspection**\n` +
      `• "What's the system health?" — Full system status\n` +
      `• "Show me the skills" — List all registered skills\n` +
      `• "What agents are available?" — Agent overview\n` +
      `• "List the domains" — Domain status\n\n` +
      `🧠 **Intelligence Profile**\n` +
      `• "Show my profile" — View your personalized intelligence profile\n` +
      `• "My preferences" — See your inferred and explicit preferences\n` +
      `• "Set my response_detail to 80" — Update a preference explicitly\n\n` +
      `🏗️ **Domain Creation**\n` +
      `• "Create a Legal Research domain" — Create a new domain with starter canvas\n` +
      `• "Make a Finance domain for trading" — Custom domain from description\n\n` +
    `📜 **Tape & Audit**\n` +
    `• "Show me the Tape" — Recent activity summary\n\n` +
    `🔌 **Plugins & Marketplace**\n` +
    `• "Show plugins" — List installed plugins\n` +
    `• "What plugins are available?" — Plugin overview\n\n` +
      `🗳️ **Proposals**\n` +
      `• "Show proposals" — Governance overview\n\n` +
      `🧪 **Simulations**\n` +
      `• "Run a simulation" — Available what-if scenarios\n` +
      `• "What-if scenarios" — Scenario listing\n\n` +
      `💡 **Tip:** Use \`⌘K\` to quickly navigate anywhere in the app.`
    );
  }

  // Default
  return `I understand you're asking about "${query}". I'm currently operating with local intelligence based on live system data.\n\nTry asking about:\n- System health\n- Skills, agents, or domains\n- **Your intelligence profile** (e.g., "Show my profile")\n- **Set preferences** (e.g., "Set my automation_level to 60")\n- Create a new domain (e.g., "Create a Legal Research domain")\n- Plugins and marketplace (e.g., "Show plugins")\n- Proposals and governance\n- Simulations and what-if scenarios\n- Tape activity and audit trail\n\nAs I evolve, I'll gain deeper reasoning capabilities and be able to take autonomous actions.`;
}
