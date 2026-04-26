"use client";

import { useSystemSnapshot, useProposals } from "@/hooks/use-api";
import { motion } from "framer-motion";
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

  const statusColor = connected
    ? "text-emerald-400"
    : checking
      ? "text-amber-400"
      : "text-red-400";

  const orbColor = connected
    ? "var(--emerald-data)"
    : checking
      ? "var(--amber-alert)"
      : "rgba(239, 68, 68, 0.5)";

  function dispatchSearch() {
    window.dispatchEvent(new CustomEvent("open-command-palette"));
  }

  return (
    <header className="h-10 flex items-center px-4 bg-card border-b border-border shrink-0 relative overflow-hidden">
      {/* Subtle grid texture background */}
      <div className="absolute inset-0 grid-texture opacity-20 pointer-events-none" />

      {/* Left section — Breadcrumb */}
      <div className="flex items-center gap-2 text-sm relative z-10">
        <motion.span
          className="text-muted-foreground font-[family-name:var(--font-plex-mono)]"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
        >
          InkosAI
        </motion.span>
        <motion.div
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <ChevronRight className="w-3 h-3 text-muted-foreground" />
        </motion.div>
        <motion.span
          className="text-foreground font-medium"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
        >
          Dashboard
        </motion.span>
      </div>

      {/* Center section — Status Banner (Chamfered) */}
      <div className="flex-1 flex justify-center min-w-0 mx-4 relative z-10">
        <motion.div
          className="chamfered-left chamfered-right flex items-center gap-2 px-4 py-1 text-xs whitespace-nowrap relative"
          style={{
            background: "linear-gradient(135deg, rgba(15, 22, 41, 0.9) 0%, rgba(21, 28, 48, 0.8) 100%)",
            border: "1px solid rgba(34, 211, 238, 0.12)",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(34, 211, 238, 0.06)",
          }}
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          whileHover={{
            boxShadow: "0 6px 16px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(34, 211, 238, 0.1)",
            borderColor: "rgba(34, 211, 238, 0.2)",
          }}
        >
          {/* Animated scan line */}
          <motion.div
            className="absolute inset-0 overflow-hidden pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
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
                duration: 3,
                repeat: Infinity,
                ease: "linear",
              }}
            />
          </motion.div>

          {/* Status Orb with Pulse Ring */}
          <div className="flex items-center gap-2">
            <motion.div
              className="status-orb w-2 h-2 rounded-full relative"
              style={{ backgroundColor: orbColor }}
              animate={{
                boxShadow: [
                  `0 0 8px ${orbColor}`,
                  `0 0 16px ${orbColor}`,
                  `0 0 8px ${orbColor}`,
                ],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            <motion.span
              className={`font-medium tracking-wide ${statusColor}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              {connected ? "CONNECTED" : checking ? "CHECKING..." : "DISCONNECTED"}
            </motion.span>
          </div>

          <span className="text-muted-foreground/40 mx-1">·</span>

          {/* Latency with terminal glow */}
          <motion.span
            className="text-muted-foreground font-[family-name:var(--font-plex-mono)] terminal-text"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35 }}
          >
            {latency}ms
          </motion.span>

          <span className="text-muted-foreground/40 mx-1">·</span>

          {/* Uptime */}
          <motion.span
            className="text-muted-foreground"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            uptime {uptime}
          </motion.span>

          {alertCount > 0 && (
            <>
              <span className="text-muted-foreground/40 mx-1">·</span>
              <motion.span
                className="text-amber-400 font-medium"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.45 }}
              >
                {alertCount} alerts
              </motion.span>
            </>
          )}
        </motion.div>
      </div>

      {/* Right section — Alerts + Actions */}
      <div className="flex items-center gap-3 relative z-10">
        {/* Alert badges with glow */}
        {idleAgents > 0 && (
          <motion.div
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div
              className="text-[10px] px-2 py-0.5 rounded-full border font-medium"
              style={{
                background: "rgba(245, 158, 11, 0.1)",
                borderColor: "rgba(245, 158, 11, 0.3)",
                color: "#F59E0B",
                boxShadow: "0 0 12px rgba(245, 158, 11, 0.15)",
              }}
            >
              {idleAgents} idle
            </div>
          </motion.div>
        )}
        {pendingProposals > 0 && (
          <motion.div
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.05 }}
          >
            <div
              className="text-[10px] px-2 py-0.5 rounded-full border font-medium"
              style={{
                background: "rgba(245, 158, 11, 0.1)",
                borderColor: "rgba(245, 158, 11, 0.3)",
                color: "#F59E0B",
                boxShadow: "0 0 12px rgba(245, 158, 11, 0.15)",
              }}
            >
              {pendingProposals} pending
            </div>
          </motion.div>
        )}
        {lowConfProposals > 0 && (
          <motion.div
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
          >
            <div
              className="text-[10px] px-2 py-0.5 rounded-full border font-medium"
              style={{
                background: "rgba(245, 158, 11, 0.1)",
                borderColor: "rgba(245, 158, 11, 0.3)",
                color: "#F59E0B",
                boxShadow: "0 0 12px rgba(245, 158, 11, 0.15)",
              }}
            >
              {lowConfProposals} low-conf
            </div>
          </motion.div>
        )}

        {/* Search button */}
        <motion.button
          onClick={dispatchSearch}
          className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground transition-colors cursor-pointer relative group"
          aria-label="Search"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Search className="w-4 h-4" />
          {/* Hover glow */}
          <div
            className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            style={{
              background: "rgba(34, 211, 238, 0.08)",
              border: "1px solid rgba(34, 211, 238, 0.15)",
            }}
          />
        </motion.button>

        {/* Notifications button */}
        <motion.button
          className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground transition-colors cursor-pointer relative group"
          aria-label="Notifications"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Bell className="w-4 h-4" />
          {/* Hover glow */}
          <div
            className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            style={{
              background: "rgba(34, 211, 238, 0.08)",
              border: "1px solid rgba(34, 211, 238, 0.15)",
            }}
          />
          {/* Notification dot (if needed) */}
          {alertCount > 0 && (
            <motion.div
              className="absolute top-1 right-1 w-2 h-2 rounded-full"
              style={{
                background: "#F59E0B",
                boxShadow: "0 0 8px rgba(245, 158, 11, 0.6)",
              }}
              animate={{
                scale: [1, 1.2, 1],
                opacity: [1, 0.8, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
              }}
            />
          )}
        </motion.button>

        {/* Avatar */}
        <motion.div
          className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-medium"
          style={{
            background: "linear-gradient(135deg, rgba(34, 211, 238, 0.15) 0%, rgba(103, 232, 249, 0.1) 100%)",
            border: "1px solid rgba(34, 211, 238, 0.2)",
            color: "#22D3EE",
          }}
          whileHover={{
            scale: 1.05,
            boxShadow: "0 0 16px rgba(34, 211, 238, 0.3)",
          }}
        >
          AK
        </motion.div>
      </div>
    </header>
  );
}
