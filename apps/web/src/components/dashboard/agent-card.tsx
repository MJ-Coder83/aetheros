"use client";

import type { AgentDescriptor } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { motion } from "framer-motion";

interface AgentCardProps {
  agent: AgentDescriptor;
  currentTask?: string;
  delay?: number;
}

const statusOrbColor = (status: string): string => {
  if (status === "active") return "var(--emerald-data)";
  if (status === "idle") return "var(--amber-alert)";
  return "rgba(148, 163, 184, 0.5)";
};

const statusGlow = (status: string): string => {
  if (status === "active") return "0 0 16px rgba(16, 185, 129, 0.4)";
  if (status === "idle") return "0 0 16px rgba(245, 158, 11, 0.3)";
  return "none";
};

export function AgentCard({ agent, currentTask, delay = 0 }: AgentCardProps) {
  const isOffline = agent.status === "offline" || agent.status === "unknown";
  const isIdle = agent.status === "idle";
  const isActive = agent.status === "active";

  const lastSeenText = agent.last_seen
    ? formatDistanceToNow(new Date(agent.last_seen), { addSuffix: false })
    : "—";

  const displayCapabilities = agent.capabilities.slice(0, 2);

  return (
    <motion.div
      className={`w-[170px] h-[100px] shrink-0 rounded-lg p-2.5 flex flex-col relative overflow-hidden corner-accent ${
        isOffline ? "opacity-50" : ""
      }`}
      initial={{ opacity: 0, x: 16, scale: 0.98 }}
      animate={{ opacity: isOffline ? 0.5 : 1, x: 0, scale: 1 }}
      transition={{
        duration: 0.4,
        delay,
        ease: [0.4, 0, 0.2, 1],
      }}
      whileHover={{
        y: -3,
        scale: 1.02,
      }}
      style={{
        background: `
          linear-gradient(135deg, rgba(34, 211, 238, 0.03) 0%, transparent 40%, rgba(103, 232, 249, 0.02) 100%),
          rgba(15, 22, 41, 0.7)
        `,
        backdropFilter: "blur(20px)",
        border: isOffline
          ? "1px dashed rgba(148, 163, 184, 0.2)"
          : "1px solid rgba(34, 211, 238, 0.12)",
        boxShadow: isActive
          ? `inset 0 1px 0 rgba(34, 211, 238, 0.06), 0 4px 12px rgba(0, 0, 0, 0.3), ${statusGlow(agent.status)}`
          : "inset 0 1px 0 rgba(34, 211, 238, 0.04), 0 2px 8px rgba(0, 0, 0, 0.2)",
      }}
    >
      {/* Animated scan line */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        initial={{ opacity: 0 }}
        whileHover={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        <motion.div
          className="absolute inset-0"
          style={{
            background: "linear-gradient(180deg, transparent 0%, rgba(34, 211, 238, 0.04) 50%, transparent 100%)",
            backgroundSize: "100% 200%",
          }}
          animate={{
            backgroundPosition: ["0% 0%", "0% 200%"],
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      </motion.div>

      {/* Header: Status Orb + Agent Name */}
      <div className="flex items-center gap-2 mb-2 relative z-10">
        {/* Pulsing Status Orb */}
        <motion.div
          className="status-orb w-2 h-2 rounded-full relative"
          style={{
            backgroundColor: statusOrbColor(agent.status),
            boxShadow: statusGlow(agent.status),
          }}
          animate={
            isActive
              ? {
                  scale: [1, 1.2, 1],
                  opacity: [0.8, 1, 0.8],
                }
              : isIdle
              ? {
                  scale: [1, 1.1, 1],
                  opacity: [0.6, 0.9, 0.6],
                }
              : {}
          }
          transition={{
            duration: isActive ? 1.5 : 2.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        {/* Agent Name with terminal glow */}
        <motion.span
          className="text-xs text-foreground truncate terminal-text-glow"
          style={{ fontFamily: "var(--font-plex-mono), monospace" }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.1 }}
        >
          {agent.name}
        </motion.span>
      </div>

      {/* Capability Tags */}
      <div className="flex gap-1 mb-2 relative z-10">
        {displayCapabilities.map((cap, index) => (
          <motion.span
            key={cap}
            className="text-[9px] px-1.5 py-0.5 rounded-full border font-medium"
            style={{
              background: "rgba(34, 211, 238, 0.06)",
              borderColor: "rgba(34, 211, 238, 0.15)",
              color: "rgba(34, 211, 238, 0.8)",
            }}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: delay + 0.15 + index * 0.05 }}
            whileHover={{
              background: "rgba(34, 211, 238, 0.12)",
              borderColor: "rgba(34, 211, 238, 0.3)",
              boxShadow: "0 0 12px rgba(34, 211, 238, 0.2)",
            }}
          >
            {cap}
          </motion.span>
        ))}
      </div>

      {/* Status Text Area */}
      <div className="mt-auto relative z-10 space-y-0.5">
        {isActive && currentTask ? (
          <>
            <motion.span
              className="text-[10px] text-muted-foreground font-[family-name:var(--font-plex-mono)]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.2 }}
            >
              {lastSeenText}
            </motion.span>
            <motion.p
              className="text-[10px] text-inkos-cyan truncate terminal-text"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.25 }}
            >
              <span className="text-muted-foreground">Running:</span> {currentTask}
            </motion.p>
          </>
        ) : isIdle ? (
          <>
            <motion.span
              className="text-[10px] text-amber-400 font-[family-name:var(--font-plex-mono)]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.2 }}
            >
              Idle: {lastSeenText}
            </motion.span>
            <motion.p
              className="text-[10px] text-muted-foreground"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.25 }}
            >
              Waiting for proposals
            </motion.p>
          </>
        ) : (
          <>
            <motion.span
              className={`text-[10px] font-[family-name:var(--font-plex-mono)] ${
                isOffline ? "text-muted-foreground" : "text-amber-400"
              }`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.2 }}
            >
              {isOffline ? "Offline" : "Last seen"}: {lastSeenText}
            </motion.span>
            <motion.p
              className="text-[10px] text-muted-foreground"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.25 }}
            >
              {isOffline ? "Maintenance mode" : "—"}
            </motion.p>
          </>
        )}
      </div>

      {/* Holographic corner accent (visual only) */}
      <div
        className="absolute top-0 right-0 w-8 h-8 pointer-events-none"
        style={{
          background: "radial-gradient(circle at top right, rgba(34, 211, 238, 0.08) 0%, transparent 60%)",
        }}
      />
    </motion.div>
  );
}
