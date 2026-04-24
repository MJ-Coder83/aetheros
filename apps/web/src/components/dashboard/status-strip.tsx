"use client";

import { useSystemSnapshot, useProposals } from "@/hooks/use-api";
import { ChevronRight, Search, Bell } from "lucide-react";

export function StatusStrip() {
  const { data: snapshot, isLoading, isError } = useSystemSnapshot();
  const { data: proposals } = useProposals();

  const idleAgents =
    snapshot?.agents.filter((a) => a.status === "idle").length ?? 0;
  const pendingProposals =
    proposals?.filter((p) => p.status === "pending_approval").length ?? 0;
  const lowConfProposals =
    proposals?.filter((p) => p.confidence_score < 0.5).length ?? 0;

  const connected = !isLoading && !isError && !!snapshot;
  const checking = isLoading;

  const latency = snapshot?.system_info?.latency_ms ?? "—";
  const uptime = snapshot?.system_info?.uptime ?? "—";

  const alertCount = idleAgents + pendingProposals + lowConfProposals;

  const dotColor = connected
    ? "bg-emerald-400"
    : checking
      ? "bg-amber-400"
      : "bg-red-400";

  const statusLabel = connected
    ? "CONNECTED"
    : checking
      ? "CHECKING..."
      : "DISCONNECTED";

  const statusColor = connected
    ? "text-emerald-400"
    : checking
      ? "text-amber-400"
      : "text-red-400";

  function dispatchSearch() {
    window.dispatchEvent(new CustomEvent("open-command-palette"));
  }

  return (
    <header className="h-8 flex items-center px-4 bg-card border-b border-border shrink-0">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">InkosAI</span>
        <ChevronRight className="w-3 h-3 text-muted-foreground" />
        <span className="text-foreground font-medium">Dashboard</span>
      </div>

      <div className="flex-1 flex justify-center min-w-0 mx-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-secondary border border-border text-xs whitespace-nowrap">
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full shrink-0 ${dotColor} pulse-dot-soft`} />
            <span className={`font-medium ${statusColor}`}>{statusLabel}</span>
          </div>
          <span className="text-muted-foreground/40">·</span>
          <span className="text-muted-foreground font-[family-name:var(--font-plex-mono)]">{latency}ms</span>
          <span className="text-muted-foreground/40">·</span>
          <span className="text-muted-foreground">uptime {uptime}</span>
          {alertCount > 0 && (
            <>
              <span className="text-muted-foreground/40">·</span>
              <span className="text-amber-400">{alertCount} alerts</span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {idleAgents > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20">
            {idleAgents} idle agents
          </span>
        )}
        {pendingProposals > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20">
            {pendingProposals} pending
          </span>
        )}
        {lowConfProposals > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20">
            {lowConfProposals} low-conf
          </span>
        )}
        <button
          onClick={dispatchSearch}
          className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          aria-label="Search"
        >
          <Search className="w-4 h-4" />
        </button>
        <button
          className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          aria-label="Notifications"
        >
          <Bell className="w-4 h-4" />
        </button>
        <div className="w-6 h-6 rounded-full bg-inkos-cyan/20 flex items-center justify-center text-[10px] font-medium text-inkos-cyan">
          AK
        </div>
      </div>
    </header>
  );
}