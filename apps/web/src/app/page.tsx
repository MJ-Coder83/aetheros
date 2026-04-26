"use client";

import {
  useSystemSnapshot,
  useRecentTape,
  useProposals,
  useSimulations,
  useGetOrCreateProfile,
} from "@/hooks/use-api";
import { motion } from "framer-motion";
import { LayoutDashboard, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

          {/* Page Header - Matching other pages style */}
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="shrink-0 border-b border-border px-4 sm:px-6 py-3 relative overflow-hidden"
            style={{
              background: "linear-gradient(180deg, rgba(15, 22, 41, 0.8) 0%, rgba(5, 8, 16, 0.6) 100%)",
              backdropFilter: "blur(20px)",
            }}
          >
            {/* Subtle grid texture */}
            <div className="absolute inset-0 grid-texture opacity-15 pointer-events-none" />

            <div className="flex items-center justify-between relative z-10">
              {/* Left: Branding */}
              <div className="flex items-center gap-3">
                <div
                  className="h-9 w-9 rounded-lg flex items-center justify-center"
                  style={{
                    background: "linear-gradient(135deg, rgba(34, 211, 238, 0.1) 0%, rgba(103, 232, 249, 0.05) 100%)",
                    border: "1px solid rgba(34, 211, 238, 0.15)",
                    boxShadow: "0 0 20px rgba(34, 211, 238, 0.2)",
                  }}
                >
                  <LayoutDashboard className="h-5 w-5 text-inkos-cyan text-glow-cyan" />
                </div>
                <div>
                  <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
                    <span className="text-inkos-cyan text-glow-cyan">Mission</span>
                    <span className="text-foreground">Control</span>
                    <span
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded border"
                      style={{
                        borderColor: "rgba(34, 211, 238, 0.3)",
                        color: "#22D3EE",
                        background: "rgba(34, 211, 238, 0.08)",
                      }}
                    >
                      LIVE
                    </span>
                  </h1>
                  <p className="text-xs text-muted-foreground">
                    {noData ? "Initializing..." : `${agents.length} agents · ${domains.length} domains · System ready`}
                  </p>
                </div>
              </div>

              {/* Right: Quick status */}
              <div className="flex items-center gap-2">
                <div
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
                  style={{
                    background: "rgba(15, 22, 41, 0.6)",
                    borderColor: "rgba(34, 211, 238, 0.1)",
                  }}
                >
                  <Activity className="h-3.5 w-3.5 text-inkos-cyan" />
                  <span className="text-xs text-muted-foreground">
                    {eventsPerMin > 0 ? `${eventsPerMin} events/min` : "No activity"}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Main Content Area - Using Card layout like other pages */}
          <div className="flex-1 overflow-auto p-4 sm:px-6 relative">
            <div className="space-y-4 max-w-[1600px] mx-auto">
              {/* Metric Tiles Row - Data Crystals */}
              <motion.div
                className="grid grid-cols-6 gap-3"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.15 }}
              >
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

              {/* Main Content Grid - Tape and Queue */}
              <motion.div
                className="grid grid-cols-[1fr_380px] gap-4 min-h-[500px]"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.25 }}
              >
                <Card
                  className="overflow-hidden border-border/50"
                  style={{
                    background: "rgba(15, 22, 41, 0.5)",
                    backdropFilter: "blur(12px)",
                  }}
                >
                  <CardHeader className="py-3 px-4 border-b border-border/50">
                    <CardTitle className="text-sm font-semibold tracking-wide flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-inkos-cyan animate-pulse" />
                      LIVE TAPE
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <TapeTable
                      entries={tapeEntries ?? []}
                      isLoading={isLoading}
                      isEmpty={!tapeEntries || tapeEntries.length === 0}
                    />
                  </CardContent>
                </Card>

                <Card
                  className="overflow-hidden border-border/50"
                  style={{
                    background: "rgba(15, 22, 41, 0.5)",
                    backdropFilter: "blur(12px)",
                  }}
                >
                  <CardContent className="p-3">
                    <QueueSidebar
                      proposals={proposals ?? []}
                      simulations={simulations ?? []}
                      isLoading={isLoading}
                    />
                  </CardContent>
                </Card>
              </motion.div>

              {/* Bottom Section - Agents and Side Panel */}
              <motion.div
                className="grid grid-cols-[1fr_320px] gap-4"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.35 }}
              >
                <Card
                  className="overflow-hidden border-border/50"
                  style={{
                    background: "rgba(15, 22, 41, 0.5)",
                    backdropFilter: "blur(12px)",
                  }}
                >
                  <CardHeader className="py-3 px-4 border-b border-border/50">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold tracking-wide">
                        AGENTS
                      </CardTitle>
                      <span className="text-[10px] text-muted-foreground font-[family-name:var(--font-plex-mono)]">
                        {agents.length} total · {activeCount} active · {idleCount} idle
                        {offlineCount > 0 ? ` · ${offlineCount} offline` : ""}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4">
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
                  </CardContent>
                </Card>

                <div className="space-y-3">
                  <ProfileSummaryCard profile={profile} isLoading={profileLoading} />
                  <DomainsStrip domains={domains} />
                  <HealthSparklines tapeEntries={tapeEntries ?? []} />
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
