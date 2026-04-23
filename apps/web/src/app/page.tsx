"use client";

import { motion } from "framer-motion";
import {
  Brain,
  ScrollText,
  Vote,
  FlaskConical,
  Cpu,
  Activity,
  Shield,
} from "lucide-react";
import { StatCard } from "@/components/stat-card";
import { StatusIndicator } from "@/components/status-indicator";
import { useSystemSnapshot, useRecentTape, useProposals, useSimulations } from "@/hooks/use-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";

const stagger = {
  animate: { transition: { staggerChildren: 0.06 } },
};
const item = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const { data: snapshot, isLoading: snapLoading } = useSystemSnapshot();
  const { data: tapeEntries } = useRecentTape(8);
  const { data: proposals } = useProposals();
  const { data: simulations } = useSimulations();

  const pendingProposals = proposals?.filter((p) => p.status === "pending_approval") ?? [];
  const completedSims = simulations?.filter((s) => s.status === "completed") ?? [];

  return (
    <motion.div
      variants={stagger}
      initial="initial"
      animate="animate"
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-8"
    >
      {/* Header */}
      <motion.div variants={item} className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            <span className="text-inkos-purple text-glow-purple">Inkos</span>
            <span className="text-inkos-cyan text-glow-cyan">AI</span>{" "}
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            System overview &amp; recent activity
          </p>
        </div>
        <StatusIndicator />
      </motion.div>

      {/* Stats grid */}
      <motion.div variants={item} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Agents"
          value={snapLoading ? "—" : snapshot?.agents.length ?? 0}
          icon={<Cpu className="h-5 w-5" />}
          accent="purple"
          sub={`${snapshot?.agents.filter((a) => a.status === "active").length ?? 0} active`}
        />
        <StatCard
          label="Skills"
          value={snapLoading ? "—" : snapshot?.skills.length ?? 0}
          icon={<Brain className="h-5 w-5" />}
          accent="cyan"
        />
        <StatCard
          label="Pending Proposals"
          value={pendingProposals.length}
          icon={<Vote className="h-5 w-5" />}
          accent="amber"
          sub="Awaiting human approval"
        />
        <StatCard
          label="Simulations"
          value={completedSims.length}
          icon={<FlaskConical className="h-5 w-5" />}
          accent="emerald"
          sub={`${simulations?.length ?? 0} total runs`}
        />
      </motion.div>

      {/* Two-column: Tape + System health */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Tape */}
        <motion.div variants={item} className="lg:col-span-2">
          <Card className="glass border-inkos-purple/20 h-full">
            <CardHeader className="flex flex-row items-center gap-2 pb-2">
              <ScrollText className="h-4 w-4 text-inkos-purple-400" />
              <CardTitle className="text-base font-semibold">
                Recent Tape Events
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(!tapeEntries || tapeEntries.length === 0) ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No Tape events yet. Start the backend to see activity.
                </p>
              ) : (
                <ul className="divide-y divide-border/30">
                  {tapeEntries.map((entry) => (
                    <li
                      key={entry.id}
                      className="flex items-center justify-between py-2.5 text-sm"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <Badge
                          variant="outline"
                          className="shrink-0 text-[10px] font-mono border-inkos-purple/30 text-inkos-purple-400"
                        >
                          {entry.event_type}
                        </Badge>
                        <span className="truncate text-muted-foreground">
                          {entry.agent_id ?? "system"}
                        </span>
                      </div>
                      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                        {formatDistanceToNow(new Date(entry.timestamp), {
                          addSuffix: true,
                        })}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* System Health */}
        <motion.div variants={item}>
          <Card className="glass border-inkos-cyan/20 h-full">
            <CardHeader className="flex flex-row items-center gap-2 pb-2">
              <Activity className="h-4 w-4 text-inkos-cyan-400" />
              <CardTitle className="text-base font-semibold">
                System Health
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {snapLoading ? (
                <div className="space-y-3 animate-pulse">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-4 rounded bg-muted/40 w-full"
                    />
                  ))}
                </div>
              ) : snapshot ? (
                <>
                  <HealthRow
                    label="Status"
                    value={snapshot.health_status}
                    good={snapshot.health_status === "healthy"}
                  />
                  <HealthRow
                    label="Tape entries"
                    value={String(snapshot.tape_stats.total_entries ?? 0)}
                    good
                  />
                  <HealthRow
                    label="Domains"
                    value={String(snapshot.domains.length)}
                    good={snapshot.domains.length > 0}
                  />
                  <HealthRow
                    label="Worktrees"
                    value={String(snapshot.active_worktrees.length)}
                    good
                  />
                  <HealthRow
                    label="Python"
                    value={snapshot.system_info.python_version?.split(" ")[0] ?? "—"}
                    good
                  />
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Backend not connected
                </p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Pending Proposals preview */}
      {pendingProposals.length > 0 && (
        <motion.div variants={item}>
          <Card className="glass border-amber-400/20">
            <CardHeader className="flex flex-row items-center gap-2 pb-2">
              <Shield className="h-4 w-4 text-amber-400" />
              <CardTitle className="text-base font-semibold">
                Pending Proposals
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-border/30">
                {pendingProposals.slice(0, 5).map((p) => (
                  <li
                    key={p.id}
                    className="flex items-center justify-between py-2.5 text-sm"
                  >
                    <span className="truncate font-medium">{p.title}</span>
                    <Badge
                      variant="outline"
                      className="shrink-0 text-[10px] border-amber-400/30 text-amber-400"
                    >
                      {p.risk_level}
                    </Badge>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </motion.div>
  );
}

function HealthRow({
  label,
  value,
  good,
}: {
  label: string;
  value: string;
  good: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={good ? "text-inkos-cyan-400" : "text-amber-400"}>
        {value}
      </span>
    </div>
  );
}
