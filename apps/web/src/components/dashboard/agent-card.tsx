import type { AgentDescriptor } from "@/types";
import { formatDistanceToNow } from "date-fns";

interface AgentCardProps {
  agent: AgentDescriptor;
  currentTask?: string;
}

function getStatusDotColor(status: string): string {
  if (status === "active") return "bg-emerald-400";
  if (status === "idle") return "bg-amber-400";
  return "bg-muted-foreground";
}

export function AgentCard({ agent, currentTask }: AgentCardProps) {
  const isOffline = agent.status === "offline" || agent.status === "unknown";
  const isIdle = agent.status === "idle";
  const isActive = agent.status === "active";

  const lastSeenText = agent.last_seen
    ? formatDistanceToNow(new Date(agent.last_seen), { addSuffix: false })
    : "—";

  const displayCapabilities = agent.capabilities.slice(0, 2);

  return (
    <div
      className={`w-[170px] h-[100px] shrink-0 bg-card rounded border border-border p-2.5 flex flex-col ${isOffline ? "opacity-60" : ""}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-2 h-2 rounded-full ${getStatusDotColor(agent.status)}`} />
        <span
          className="text-xs text-foreground truncate"
          style={{ fontFamily: "var(--font-plex-mono), monospace" }}
        >
          {agent.name}
        </span>
      </div>

      <div className="flex gap-1 mb-2">
        {displayCapabilities.map((cap) => (
          <span
            key={cap}
            className="text-[9px] px-1 py-0.5 rounded bg-secondary text-muted-foreground"
          >
            {cap}
          </span>
        ))}
      </div>

      <div className="mt-auto">
        {isActive && currentTask ? (
          <>
            <span className="text-[10px] text-muted-foreground">
              Last seen: {lastSeenText}
            </span>
            <p className="text-[10px] text-muted-foreground truncate">
              Running: {currentTask}
            </p>
          </>
        ) : isIdle ? (
          <>
            <span className="text-[10px] text-muted-foreground">
              Idle: {lastSeenText}
            </span>
            <p className="text-[10px] text-muted-foreground">Waiting for proposals</p>
          </>
        ) : (
          <>
            <span className="text-[10px] text-muted-foreground">
              {isOffline ? "Offline: " : "Last seen: "}
              {lastSeenText}
            </span>
            <p className="text-[10px] text-muted-foreground">
              {isOffline ? "Maintenance mode" : "—"}
            </p>
          </>
        )}
      </div>
    </div>
  );
}