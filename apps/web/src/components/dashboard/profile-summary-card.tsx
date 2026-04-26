"use client";

import { motion } from "framer-motion";
import { Brain, Star, Settings2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserProfile } from "@/types";

const levelColors: Record<string, string> = {
  novice: "text-gray-400",
  intermediate: "text-blue-400",
  advanced: "text-purple-400",
  expert: "text-inkos-cyan",
};

export function ProfileSummaryCard({
  profile,
  isLoading,
}: {
  profile: UserProfile | null | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <motion.div
        className="p-3 space-y-2 rounded-lg"
        style={{
          background: "rgba(15, 22, 41, 0.6)",
          border: "1px solid rgba(34, 211, 238, 0.08)",
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="h-3 w-24 bg-secondary animate-pulse rounded" />
        <div className="h-2 w-full bg-secondary animate-pulse rounded" />
        <div className="h-2 w-3/4 bg-secondary animate-pulse rounded" />
      </motion.div>
    );
  }

  if (!profile) {
    return (
      <div className="p-3 text-xs text-muted-foreground/50 rounded-lg"
        style={{
          background: "rgba(15, 22, 41, 0.5)",
          border: "1px dashed rgba(34, 211, 238, 0.06)",
        }}
      >
        No profile data
      </div>
    );
  }

  const intel = profile.intelligence;
  const domainExps = Object.values(intel.domain_expertise)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
  const topPrefs = Object.values(intel.preferences)
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3);

  return (
    <motion.div
      className="p-3 space-y-2.5 rounded-lg relative overflow-hidden"
      style={{
        background: `
          linear-gradient(135deg, rgba(34, 211, 238, 0.03) 0%, transparent 50%, rgba(124, 122, 237, 0.02) 100%),
          rgba(15, 22, 41, 0.7)
        `,
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(34, 211, 238, 0.1)",
        boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.04), 0 4px 8px rgba(0, 0, 0, 0.2)",
      }}
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.5 }}
      whileHover={{
        borderColor: "rgba(34, 211, 238, 0.2)",
        boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.08), 0 8px 16px rgba(0, 0, 0, 0.3)",
      }}
    >
      {/* Animated glow corner */}
      <div
        className="absolute top-0 right-0 w-16 h-16 pointer-events-none"
        style={{
          background: "radial-gradient(circle at top right, rgba(34, 211, 238, 0.08) 0%, transparent 60%)",
        }}
      />

      <div className="flex items-center justify-between relative z-10">
        <span className="text-xs font-semibold text-foreground flex items-center gap-1.5 tracking-wide">
          <motion.div
            animate={{
              textShadow: [
                "0 0 8px rgba(34, 211, 238, 0.3)",
                "0 0 16px rgba(34, 211, 238, 0.5)",
                "0 0 8px rgba(34, 211, 238, 0.3)",
              ],
            }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            <Brain className="h-3.5 w-3.5 text-inkos-cyan" />
          </motion.div>
          PROFILE
        </span>
        <motion.a
          href="/profile"
          className="text-[10px] text-inkos-cyan hover:underline font-[family-name:var(--font-plex-mono)]"
          whileHover={{ x: 2 }}
        >
          View →
        </motion.a>
      </div>

      {/* Stats Row */}
      <div className="flex gap-3 text-center relative z-10">
        <div className="flex-1">
          <motion.div
            className="text-sm font-bold tabular-nums terminal-text-glow"
            style={{ color: "#22D3EE" }}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.6 }}
          >
            {intel.interaction_summary.total_interactions}
          </motion.div>
          <div className="text-[9px] uppercase text-muted-foreground">Interactions</div>
        </div>
        <div className="flex-1">
          <motion.div
            className="text-sm font-bold tabular-nums"
            style={{
              color: "#10B981",
              textShadow: "0 0 12px rgba(16, 185, 129, 0.3)",
            }}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.65 }}
          >
            {Math.round(intel.interaction_summary.approval_rate * 100)}%
          </motion.div>
          <div className="text-[9px] uppercase text-muted-foreground">Approve</div>
        </div>
        <div className="flex-1">
          <motion.div
            className="text-sm font-bold tabular-nums"
            style={{
              color: "#F59E0B",
              textShadow: "0 0 12px rgba(245, 158, 11, 0.3)",
            }}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.7 }}
          >
            {Math.round(intel.interaction_summary.avg_depth * 100)}%
          </motion.div>
          <div className="text-[9px] uppercase text-muted-foreground">Depth</div>
        </div>
      </div>

      {/* Domain Expertise */}
      {domainExps.length > 0 && (
        <motion.div
          className="space-y-1 relative z-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.75 }}
        >
          <div className="flex items-center gap-1 text-muted-foreground">
            <Star className="h-2.5 w-2.5" />
            <span className="text-[9px] uppercase tracking-wider">Domains</span>
          </div>
          {domainExps.map((exp, i) => (
            <motion.div
              key={exp.domain_id}
              className="flex items-center justify-between text-[11px]"
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.8 + i * 0.05 }}
            >
              <span className="truncate text-muted-foreground font-[family-name:var(--font-plex-mono)]">{exp.domain_id}</span>
              <span className={cn("font-mono", levelColors[exp.level] ?? "text-muted-foreground")}>
                {exp.level}
              </span>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Preferences */}
      {topPrefs.length > 0 && (
        <motion.div
          className="space-y-1 relative z-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.85 }}
        >
          <div className="flex items-center gap-1 text-muted-foreground">
            <Settings2 className="h-2.5 w-2.5" />
            <span className="text-[9px] uppercase tracking-wider">Prefs</span>
          </div>
          {topPrefs.map((pref, i) => (
            <motion.div
              key={pref.category}
              className="flex items-center justify-between text-[11px]"
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.9 + i * 0.05 }}
            >
              <span className="truncate text-muted-foreground font-[family-name:var(--font-plex-mono)]">{pref.category.replace(/_/g, " ")}</span>
              <span className="font-mono tabular-nums text-muted-foreground terminal-text">
                {Math.round(pref.value * 100)}%
              </span>
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Footer */}
      <motion.div
        className="flex items-center justify-between text-[9px] text-muted-foreground/40 pt-1 border-t border-border relative z-10"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.95 }}
      >
        <span className="uppercase font-[family-name:var(--font-plex-mono)]">{profile.status}</span>
        <span className="font-[family-name:var(--font-plex-mono)]">v{profile.version} · {intel.adaptation_count} adaptations</span>
      </motion.div>
    </motion.div>
  );
}
