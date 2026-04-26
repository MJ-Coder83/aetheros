"use client";

import { motion } from "framer-motion";
import { Sparkline } from "./sparkline";
import type { TapeEntry } from "@/types";

interface HealthSparklinesProps {
  tapeEntries: TapeEntry[];
}

function deriveEventRate(entries: TapeEntry[]): number[] {
  if (!entries || entries.length === 0) {
    return [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
  }

  const now = Date.now();
  const buckets: number[] = Array(10).fill(0);

  entries.forEach((entry) => {
    const age = now - new Date(entry.timestamp).getTime();
    const bucket = Math.floor(age / 60000);
    if (bucket >= 0 && bucket < 10) {
      buckets[9 - bucket]++;
    }
  });

  const max = Math.max(...buckets, 1);
  return buckets.map((v) => v / max);
}

function deriveApprovalRate(entries: TapeEntry[]): number[] {
  if (!entries || entries.length === 0) {
    return [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
  }

  const now = Date.now();
  const windowMs = 10 * 60 * 1000;
  const bucketMs = 60000;
  const buckets: { approved: number; rejected: number }[] = Array(10)
    .fill(null)
    .map(() => ({ approved: 0, rejected: 0 }));

  entries.forEach((entry) => {
    const age = now - new Date(entry.timestamp).getTime();
    if (age > windowMs) return;
    const bucket = Math.floor(age / bucketMs);
    if (bucket < 0 || bucket >= 10) return;
    const idx = 9 - bucket;
    if (entry.event_type.includes("proposal_approved")) {
      buckets[idx].approved++;
    } else if (entry.event_type.includes("proposal_rejected")) {
      buckets[idx].rejected++;
    }
  });

  return buckets.map(({ approved, rejected }) => {
    const total = approved + rejected;
    return total > 0 ? approved / total : 0.5;
  });
}

function deriveSimSuccessRate(entries: TapeEntry[]): number[] {
  if (!entries || entries.length === 0) {
    return [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5];
  }

  const now = Date.now();
  const windowMs = 10 * 60 * 1000;
  const bucketMs = 60000;
  const buckets: { completed: number; failed: number }[] = Array(10)
    .fill(null)
    .map(() => ({ completed: 0, failed: 0 }));

  entries.forEach((entry) => {
    const age = now - new Date(entry.timestamp).getTime();
    if (age > windowMs) return;
    const bucket = Math.floor(age / bucketMs);
    if (bucket < 0 || bucket >= 10) return;
    const idx = 9 - bucket;
    if (entry.event_type === "simulation.completed") {
      buckets[idx].completed++;
    } else if (
      entry.event_type.includes("simulation.failed") ||
      entry.event_type.includes("timeout")
    ) {
      buckets[idx].failed++;
    }
  });

  return buckets.map(({ completed, failed }) => {
    const total = completed + failed;
    return total > 0 ? completed / total : 0.5;
  });
}

export function HealthSparklines({ tapeEntries }: HealthSparklinesProps) {
  const eventRateData = deriveEventRate(tapeEntries);
  const approvalRateData = deriveApprovalRate(tapeEntries);
  const simSuccessData = deriveSimSuccessRate(tapeEntries);

  return (
    <motion.div
      className="flex-1 rounded-lg p-2 relative overflow-hidden"
      style={{
        background: `
          linear-gradient(135deg, rgba(34, 211, 238, 0.02) 0%, transparent 50%, rgba(16, 185, 129, 0.02) 100%),
          rgba(15, 22, 41, 0.7)
        `,
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(34, 211, 238, 0.1)",
        boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.04), 0 4px 8px rgba(0, 0, 0, 0.2)",
      }}
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.6 }}
    >
      {/* Animated glow overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at bottom left, rgba(16, 185, 129, 0.04) 0%, transparent 50%)",
        }}
      />

      <span className="text-[10px] font-semibold text-foreground mb-2 block tracking-wide relative z-10">
        HEALTH
      </span>
      <div className="space-y-2 relative z-10">
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-muted-foreground w-20 font-[family-name:var(--font-plex-mono)]">Event rate</span>
          <Sparkline data={eventRateData} width={100} height={16} color="cyan" animated />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-muted-foreground w-20 font-[family-name:var(--font-plex-mono)]">Approval rate</span>
          <Sparkline
            data={approvalRateData}
            width={100}
            height={16}
            color="emerald"
            animated
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-muted-foreground w-20 font-[family-name:var(--font-plex-mono)]">Sim success</span>
          <Sparkline
            data={simSuccessData}
            width={100}
            height={16}
            color="emerald"
            animated
          />
        </div>
      </div>
    </motion.div>
  );
}
