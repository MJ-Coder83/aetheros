"use client";

import { motion } from "framer-motion";
import { Sparkline } from "./sparkline";

type AccentColor = "text" | "cyan" | "emerald" | "amber" | "red";

interface MetricTileProps {
  label: string;
  value: string | number;
  delta?: string;
  accent?: AccentColor;
  sparklineData?: number[];
  delay?: number;
}

const accentColorMap: Record<AccentColor, string> = {
  text: "text-foreground",
  cyan: "text-inkos-cyan",
  emerald: "text-emerald-400",
  amber: "text-amber-400",
  red: "text-red-400",
};

const sparklineColorMap: Record<AccentColor, "cyan" | "emerald" | "amber" | "violet"> = {
  text: "cyan",
  cyan: "cyan",
  emerald: "emerald",
  amber: "amber",
  red: "cyan",
};

const accentGlowMap: Record<AccentColor, string> = {
  text: "rgba(34, 211, 238, 0.15)",
  cyan: "rgba(34, 211, 238, 0.2)",
  emerald: "rgba(16, 185, 129, 0.2)",
  amber: "rgba(245, 158, 11, 0.2)",
  red: "rgba(239, 68, 68, 0.2)",
};

export function MetricTile({
  label,
  value,
  delta,
  accent = "text",
  sparklineData,
  delay = 0,
}: MetricTileProps) {
  const deltaColor =
    delta && delta.startsWith("+")
      ? "text-emerald-400"
      : delta?.startsWith("-")
        ? "text-amber-400"
        : "text-muted-foreground";

  const glowColor = accentGlowMap[accent];

  return (
    <motion.div
      className="flex-1 h-16 flex flex-col justify-between py-2 px-3 relative corner-accent"
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.4,
        delay,
        ease: [0.4, 0, 0.2, 1],
      }}
      whileHover={{
        y: -2,
        scale: 1.02,
      }}
      style={{
        background: `
          linear-gradient(135deg, rgba(34, 211, 238, 0.04) 0%, transparent 50%, rgba(103, 232, 249, 0.02) 100%),
          rgba(15, 22, 41, 0.7)
        `,
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(34, 211, 238, 0.12)",
        borderRadius: "var(--radius-lg)",
        boxShadow: `
          inset 0 1px 0 rgba(34, 211, 238, 0.06),
          0 4px 12px rgba(0, 0, 0, 0.3),
          0 0 24px ${glowColor}
        `,
      }}
    >
      {/* Animated scan line on hover */}
      <motion.div
        className="absolute inset-0 overflow-hidden rounded pointer-events-none"
        initial={{ opacity: 0 }}
        whileHover={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        <motion.div
          className="absolute inset-0"
          style={{
            background: "linear-gradient(180deg, transparent 0%, rgba(34, 211, 238, 0.06) 50%, transparent 100%)",
            backgroundSize: "100% 200%",
          }}
          animate={{
            backgroundPosition: ["0% 0%", "0% 200%"],
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      </motion.div>

      {/* Label */}
      <motion.span
        className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: delay + 0.15 }}
      >
        {label}
      </motion.span>

      {/* Value and delta */}
      <div className="flex items-end gap-2 relative z-10">
        <motion.span
          className={`text-3xl font-semibold tabular-nums ${accentColorMap[accent]}`}
          style={{
            fontFamily: "var(--font-plex-mono), monospace",
            textShadow: accent === "cyan" || accent === "text"
              ? "0 0 12px rgba(34, 211, 238, 0.2)"
              : "none",
          }}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{
            delay: delay + 0.2,
            duration: 0.3,
          }}
        >
          {value}
        </motion.span>
        {delta && (
          <motion.span
            className={`text-[10px] mb-1 font-medium ${deltaColor}`}
            style={{ fontFamily: "var(--font-plex-mono), monospace" }}
            initial={{ opacity: 0, x: 4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + 0.25 }}
          >
            {delta}
          </motion.span>
        )}
      </div>

      {/* Sparkline */}
      {sparklineData && sparklineData.length >= 2 && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: delay + 0.3 }}
          className="relative z-10"
        >
          <Sparkline
            data={sparklineData}
            width={60}
            height={16}
            color={sparklineColorMap[accent]}
            animated
          />
        </motion.div>
      )}
    </motion.div>
  );
}
