"use client";

import {
  useSystemSnapshot,
  useRecentTape,
  useProposals,
  useSimulations,
  useGetOrCreateProfile,
} from "@/hooks/use-api";
import { LeftRail } from "@/components/dashboard/left-rail";
import { StatusStrip } from "@/components/dashboard/status-strip";
import { MetricTile } from "@/components/dashboard/metric-tile";
import { TapeTable } from "@/components/dashboard/tape-table";
import { QueueSidebar } from "@/components/dashboard/queue-sidebar";
import { AgentCard } from "@/components/dashboard/agent-card";
import { DomainsStrip } from "@/components/dashboard/domains-strip";
import { HealthSparklines } from "@/components/dashboard/health-sparklines";
import { ProfileSummaryCard } from "@/components/dashboard/profile-summary-card";
import { HoloBackground } from "@/components/dashboard/holo-background";
import { motion } from "framer-motion";

function deriveEventsPerMinute(entries: { timestamp: string }[]): number {
  if (!entries || entries.length === 0) return 0;
  const now = Date.now();
  const oneMinuteAgo = now - 60000;
  const recent = entries.filter(
    (e) => new Date(e.timestamp).getTime() > oneMinuteAgo
  );
  return recent.length;
}

function getCurrentTask(
  agentId: string,
  entries: { agent_id: string | null; event_type: string; payload: Record<string, string | number | boolean | null> }[]
): string | undefined {
  const entry = entries.find(
    (e) => e.agent_id === agentId && e.event_type.includes("proposal")
  );
  if (!entry) return undefined;
  const title = entry.payload?.title;
  if (typeof title === "string") {
    return title.length > 20 ? title.slice(0, 20) + "…" : title;
  }
  return undefined;
}

export default function DashboardPage() {
  const { data: snapshot, isLoading: snapLoading, isError: snapError } = useSystemSnapshot();
  const { data: tapeEntries, isLoading: tapeLoading } = useRecentTape(50);
  const { data: proposals, isLoading: propLoading } = useProposals();
  const { data: simulations, isLoading: simLoading } = useSimulations();
  const { data: profile, isLoading: profileLoading } = useGetOrCreateProfile("default");

  const pendingProposals =
    proposals?.filter((p) => p.status === "pending_approval") ?? [];
  const runningSims = simulations?.filter((s) => s.status === "running") ?? [];

  const agents = snapshot?.agents ?? [];
  const skills = snapshot?.skills ?? [];
  const domains = snapshot?.domains ?? [];

  const eventsPerMin = deriveEventsPerMinute(tapeEntries ?? []);

  const isLoading = snapLoading || tapeLoading || propLoading || simLoading;
  const noData = snapLoading || snapError || !snapshot;
  const val = <T extends string | number>(v: T): T | "—" => noData ? "—" : v;

  const activeCount = agents.filter((a) => a.status === "active").length;
  const idleCount = agents.filter((a) => a.status === "idle").length;
  const offlineCount = agents.filter(
    (a) => a.status === "offline" || a.status === "unknown"
  ).length;

  return (
    <>
      {/* Holographic background layers */}
      <HoloBackground />

      {/* Main layout */}
      <div className="flex flex-1 min-h-0 w-full overflow-hidden relative">
        {/* Left Rail - Command Pillar */}
        <LeftRail />

        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Status Strip - System Banner */}
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <StatusStrip />
          </motion.div>

          {/* Metric Tiles - Data Crystals */}
          <motion.div
            className="h-[110px] shrink-0 border-b border-border grid-texture flex items-center px-4 gap-3 relative"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            {/* Subtle glow overlay */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: "radial-gradient(ellipse at 50% 0%, rgba(34, 211, 238, 0.06) 0%, transparent 50%)",
              }}
            />

            <MetricTile
              label="AGENTS"
              value={val(agents.length)}
              accent="emerald"
              sparklineData={agents.length > 0 ? [3, 4, 5, 4, 6, 5, 7] : undefined}
              delay={0.15}
            />
            <MetricTile
              label="SKILLS"
              value={val(skills.length)}
              accent="text"
              sparklineData={skills.length > 0 ? [8, 9, 10, 9, 11, 10, 12] : undefined}
              delay={0.2}
            />
            <MetricTile
              label="DOMAINS"
              value={val(domains.length)}
              accent="text"
              sparklineData={domains.length > 0 ? [1, 2, 2, 3, 2, 3, 3] : undefined}
              delay={0.25}
            />
            <MetricTile
              label="PENDING"
              value={val(pendingProposals.length)}
              accent={pendingProposals.length > 0 ? "amber" : "text"}
              sparklineData={pendingProposals.length > 0 ? [0, 1, 1, 2, 1, 2, 2] : undefined}
              delay={0.3}
            />
            <MetricTile
              label="RUNNING SIMS"
              value={val(runningSims.length)}
              accent={runningSims.length > 0 ? "cyan" : "text"}
              sparklineData={runningSims.length > 0 ? [0, 0, 1, 0, 1, 1, 1] : undefined}
              delay={0.35}
            />
            <MetricTile
              label="EVENTS/MIN"
              value={noData ? "—" : eventsPerMin}
              accent={eventsPerMin > 10 ? "emerald" : "text"}
              sparklineData={eventsPerMin > 0 ? [5, 8, 6, 12, 9, 14, eventsPerMin] : undefined}
              delay={0.4}
            />
          </motion.div>

          {/* Main Content Area */}
          <div className="flex-1 flex overflow-hidden relative">
            <motion.div
              className="flex-1 flex"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <TapeTable
                entries={tapeEntries ?? []}
                isLoading={isLoading}
                isEmpty={!tapeEntries || tapeEntries.length === 0}
              />
              <QueueSidebar
                proposals={proposals ?? []}
                simulations={simulations ?? []}
                isLoading={isLoading}
              />
            </motion.div>
          </div>

          {/* Bottom Section - Agent Cards + Side Panel */}
          <motion.div
            className="h-[185px] shrink-0 border-t border-border flex relative"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            {/* Holographic atmosphere overlay */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: "radial-gradient(ellipse at 100% 100%, rgba(34, 211, 238, 0.04) 0%, transparent 40%)",
              }}
            />

            <div className="flex-1 p-4 border-r border-border overflow-x-auto relative z-10">
              <div className="flex items-center justify-between mb-3">
                <motion.span
                  className="text-xs font-semibold text-foreground tracking-wide"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                >
                  AGENTS
                </motion.span>
                <motion.span
                  className="text-[10px] text-muted-foreground font-[family-name:var(--font-plex-mono)]"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.55 }}
                >
                  {agents.length} total · {activeCount} active · {idleCount} idle
                  {offlineCount > 0 ? ` · ${offlineCount} offline` : ""}
                </motion.span>
              </div>
              <div className="flex gap-3 overflow-x-auto pb-2">
                {isLoading && agents.length === 0
                  ? Array.from({ length: 4 }).map((_, i) => (
                      <div
                        key={i}
                        className="w-[170px] h-[100px] shrink-0 bg-card rounded border border-border p-2.5 flex flex-col"
                      >
                        <div className="h-3 w-20 bg-secondary animate-pulse rounded mb-2" />
                        <div className="h-2 w-16 bg-secondary animate-pulse rounded mb-2" />
                        <div className="mt-auto h-2 w-24 bg-secondary animate-pulse rounded" />
                      </div>
                    ))
                  : agents.map((agent, index) => (
                      <AgentCard
                        key={agent.agent_id}
                        agent={agent}
                        currentTask={getCurrentTask(agent.agent_id, tapeEntries ?? [])}
                        delay={index * 0.05}
                      />
                    ))}
              </div>
            </div>

            <motion.div
              className="w-[320px] p-4 flex flex-col shrink-0 gap-2 relative z-10"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.5 }}
            >
              <ProfileSummaryCard profile={profile} isLoading={profileLoading} />
              <DomainsStrip domains={domains} />
              <HealthSparklines tapeEntries={tapeEntries ?? []} />
            </motion.div>
          </motion.div>
        </div>
      </div>
    </>
  );
}
