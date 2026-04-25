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
    <div className="flex flex-1 min-h-0 w-full overflow-hidden bg-background">
      <LeftRail />

      <div className="flex-1 flex flex-col overflow-hidden">
        <StatusStrip />

        <div className="h-[110px] shrink-0 border-b border-border grid-texture flex items-center px-4 gap-3">
          <MetricTile
            label="AGENTS"
            value={val(agents.length)}
            accent="emerald"
            sparklineData={agents.length > 0 ? [3, 4, 5, 4, 6, 5, 7] : undefined}
          />
          <MetricTile
            label="SKILLS"
            value={val(skills.length)}
            accent="text"
            sparklineData={skills.length > 0 ? [8, 9, 10, 9, 11, 10, 12] : undefined}
          />
          <MetricTile
            label="DOMAINS"
            value={val(domains.length)}
            accent="text"
            sparklineData={domains.length > 0 ? [1, 2, 2, 3, 2, 3, 3] : undefined}
          />
          <MetricTile
            label="PENDING"
            value={val(pendingProposals.length)}
            accent={pendingProposals.length > 0 ? "amber" : "text"}
            sparklineData={pendingProposals.length > 0 ? [0, 1, 1, 2, 1, 2, 2] : undefined}
          />
          <MetricTile
            label="RUNNING SIMS"
            value={val(runningSims.length)}
            accent={runningSims.length > 0 ? "cyan" : "text"}
            sparklineData={runningSims.length > 0 ? [0, 0, 1, 0, 1, 1, 1] : undefined}
          />
          <MetricTile
            label="EVENTS/MIN"
            value={noData ? "—" : eventsPerMin}
            accent={eventsPerMin > 10 ? "emerald" : "text"}
            sparklineData={eventsPerMin > 0 ? [5, 8, 6, 12, 9, 14, eventsPerMin] : undefined}
          />
        </div>

        <div className="flex-1 flex overflow-hidden">
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
        </div>

        <div className="h-[185px] shrink-0 border-t border-border flex">
          <div className="flex-1 p-4 border-r border-border overflow-x-auto">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-foreground">AGENTS</span>
              <span className="text-[10px] text-muted-foreground">
                {agents.length} total · {activeCount} active · {idleCount} idle
                {offlineCount > 0 ? ` · ${offlineCount} offline` : ""}
              </span>
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
                : agents.map((agent) => (
                    <AgentCard
                      key={agent.agent_id}
                      agent={agent}
                      currentTask={getCurrentTask(agent.agent_id, tapeEntries ?? [])}
                    />
                  ))}
            </div>
          </div>

          <div className="w-[320px] p-4 flex flex-col shrink-0 gap-2">
            <ProfileSummaryCard profile={profile} isLoading={profileLoading} />
            <DomainsStrip domains={domains} />
            <HealthSparklines tapeEntries={tapeEntries ?? []} />
          </div>
        </div>
      </div>
    </div>
  );
}