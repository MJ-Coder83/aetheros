import { format } from "date-fns";
import { ScrollText } from "lucide-react";
import type { TapeEntry } from "@/types";

interface TapeTableProps {
  entries: TapeEntry[];
  isLoading: boolean;
  isEmpty: boolean;
}

function getEventTypeColor(eventType: string): string {
  if (eventType.includes("skill_evolution"))
    return "border-violet-400/30 text-violet-400";
  if (
    eventType.includes("proposal_approved") ||
    eventType === "simulation.completed"
  )
    return "border-emerald-500/30 text-emerald-400";
  if (
    eventType.includes("proposal_rejected") ||
    eventType.includes("failed") ||
    eventType.includes("timeout")
  )
    return "border-red-400/30 text-red-400";
  if (eventType.startsWith("prime.") || eventType.startsWith("simulation."))
    return "border-inkos-cyan/30 text-inkos-cyan";
  return "border-white/10 text-muted-foreground";
}

function formatPayload(payload: Record<string, string | number | boolean | null>): string {
  const cleaned = JSON.stringify(payload)
    .replace(/[{}"]/g, "")
    .replace(/,/g, ", ");
  return cleaned.length > 80 ? cleaned.slice(0, 80) + "…" : cleaned;
}

function SkeletonRow({ index }: { index: number }) {
  return (
    <tr
      className={`border-b border-border/50 ${index % 2 === 1 ? "bg-secondary/30" : ""}`}
    >
      <td className="py-1 px-2">
        <div className="h-3 w-20 rounded bg-secondary animate-pulse" />
      </td>
      <td className="py-1 px-2">
        <div className="h-3 w-32 rounded bg-secondary animate-pulse" />
      </td>
      <td className="py-1 px-2">
        <div className="h-3 w-16 rounded bg-secondary animate-pulse" />
      </td>
      <td className="py-1 px-2">
        <div className="h-3 w-48 rounded bg-secondary animate-pulse" />
      </td>
    </tr>
  );
}

export function TapeTable({ entries, isLoading, isEmpty }: TapeTableProps) {
  return (
    <div className="flex-1 flex flex-col p-4 pr-2 overflow-hidden">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">LIVE TAPE</span>
          <div className="w-2 h-2 rounded-full bg-inkos-cyan pulse-dot-soft" />
          <span className="text-xs text-muted-foreground">
            {entries.length} events
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-card rounded border border-border">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-secondary border-b border-border">
            <tr className="text-muted-foreground">
              <th className="text-left py-1.5 px-2 font-normal">TIME</th>
              <th className="text-left py-1.5 px-2 font-normal">TYPE</th>
              <th className="text-left py-1.5 px-2 font-normal">AGENT</th>
              <th className="text-left py-1.5 px-2 font-normal">PAYLOAD</th>
            </tr>
          </thead>
          <tbody
            className="text-[11px]"
            style={{ fontFamily: "var(--font-plex-mono), monospace" }}
          >
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <SkeletonRow key={i} index={i} />
              ))
            ) : isEmpty ? (
              <tr>
                <td colSpan={4} className="py-12 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <ScrollText className="w-6 h-6 text-muted-foreground/40" />
                    <p className="text-sm text-muted-foreground">
                      No events yet — awaiting backend connection
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              entries.map((entry, index) => (
                <tr
                  key={entry.id}
                  className={`border-b border-border/50 hover:bg-secondary/50 ${index % 2 === 1 ? "bg-secondary/30" : ""}`}
                >
                  <td className="py-1 px-2 text-muted-foreground tabular-nums">
                    {format(new Date(entry.timestamp), "HH:mm:ss.SSS")}
                  </td>
                  <td className="py-1 px-2">
                    <span
                      className={`px-1.5 py-0.5 rounded border text-[10px] ${getEventTypeColor(entry.event_type)}`}
                    >
                      {entry.event_type}
                    </span>
                  </td>
                  <td className="py-1 px-2 text-muted-foreground truncate max-w-[120px]">
                    {entry.agent_id ?? "system"}
                  </td>
                  <td className="py-1 px-2 text-muted-foreground truncate max-w-[300px]">
                    {formatPayload(entry.payload)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}