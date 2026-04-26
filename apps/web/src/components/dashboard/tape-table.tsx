"use client";

import { format } from "date-fns";
import { motion } from "framer-motion";
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
    <motion.tr
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.05 }}
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
    </motion.tr>
  );
}

export function TapeTable({ entries, isLoading, isEmpty }: TapeTableProps) {
  return (
    <div className="flex-1 flex flex-col p-4 pr-2 overflow-hidden">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground tracking-wide">LIVE TAPE</span>
          <motion.div
            className="w-2 h-2 rounded-full bg-inkos-cyan"
            animate={{
              boxShadow: [
                "0 0 8px rgba(34, 211, 238, 0.4)",
                "0 0 16px rgba(34, 211, 238, 0.6)",
                "0 0 8px rgba(34, 211, 238, 0.4)",
              ],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
          <span className="text-xs text-muted-foreground font-[family-name:var(--font-plex-mono)]">
            {entries.length} events
          </span>
        </div>
      </div>

      <div
        className="flex-1 overflow-y-auto rounded-lg relative"
        style={{
          background: "rgba(15, 22, 41, 0.5)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(34, 211, 238, 0.1)",
          boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.04)",
        }}
      >
        {/* Grid texture overlay */}
        <div className="absolute inset-0 grid-texture opacity-15 pointer-events-none" />

        <table className="w-full text-xs relative z-10">
          <thead className="sticky top-0 z-20">
            <tr
              className="text-muted-foreground"
              style={{
                background: "rgba(21, 28, 48, 0.9)",
                backdropFilter: "blur(8px)",
                borderBottom: "1px solid rgba(34, 211, 238, 0.12)",
              }}
            >
              <th className="text-left py-2 px-2 font-normal text-[10px] uppercase tracking-wider">TIME</th>
              <th className="text-left py-2 px-2 font-normal text-[10px] uppercase tracking-wider">TYPE</th>
              <th className="text-left py-2 px-2 font-normal text-[10px] uppercase tracking-wider">AGENT</th>
              <th className="text-left py-2 px-2 font-normal text-[10px] uppercase tracking-wider">PAYLOAD</th>
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
                  <motion.div
                    className="flex flex-col items-center gap-2"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                  >
                    <ScrollText className="w-6 h-6 text-muted-foreground/40" />
                    <p className="text-sm text-muted-foreground">
                      No events yet — awaiting backend connection
                    </p>
                  </motion.div>
                </td>
              </tr>
            ) : (
              entries.map((entry, index) => (
                <motion.tr
                  key={entry.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    duration: 0.3,
                    delay: Math.min(index * 0.03, 0.3),
                  }}
                  whileHover={{
                    background: "rgba(34, 211, 238, 0.04)",
                  }}
                  className={`border-b border-border/50 cursor-default ${index % 2 === 1 ? "bg-secondary/20" : ""}`}
                >
                  <td className="py-1.5 px-2 text-muted-foreground tabular-nums terminal-text">
                    {format(new Date(entry.timestamp), "HH:mm:ss.SSS")}
                  </td>
                  <td className="py-1.5 px-2">
                    <motion.span
                      className={`px-2 py-0.5 rounded text-[10px] font-medium border ${getEventTypeColor(entry.event_type)}`}
                      style={{
                        background: "rgba(15, 22, 41, 0.6)",
                      }}
                      whileHover={{
                        boxShadow: "0 0 12px currentColor",
                      }}
                    >
                      {entry.event_type}
                    </motion.span>
                  </td>
                  <td className="py-1.5 px-2 text-muted-foreground truncate max-w-[120px]">
                    {entry.agent_id ?? "system"}
                  </td>
                  <td className="py-1.5 px-2 text-muted-foreground truncate max-w-[300px]">
                    {formatPayload(entry.payload)}
                  </td>
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
